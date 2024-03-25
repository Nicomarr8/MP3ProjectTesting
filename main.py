import time, tkinter, eyed3, pygame, os, threading, random, json
from tkinter import font
from tkinter import ttk
from tkinter import filedialog
from functools import partial
from PIL import ImageTk,Image

#Only applies to Windows systems
try:
    from ctypes import windll, byref, sizeof, c_int
except:
    pass

class Window(tkinter.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Establish style of application window
        self.title("Pufferfish v0.2")
        try:
            self.iconbitmap("PufferfishLogo.ico")
        except:
            pass
        try:
            HWND = windll.user32.GetParent(self.winfo_id())
            AppColor = 0x00332823
            windll.dwmapi.DwmSetWindowAttribute(HWND,35,byref(c_int(AppColor)),sizeof(c_int))
        except:
            pass

        #Configure application geometry
        self.geometry(f"{int(self.winfo_screenwidth() * (3/4))}x{int(self.winfo_screenheight() * (3/4))}")
        self.minsize(600, 480)
        self.configure(background = "gray")
        self.buttonImages = {}
        self.canvases = {}
        self.frames = {}

        #Configure application and file data
        self.songs = []
        self.songButtons = []
        self.playlists = {"likedSongs":[]}
        self.idCounter = 0
        self.paused = True
        self.currentSong = 0
        self.likedMode = False
        self.loop = False
        self.shuffle = False
        self.scrollSpeed = 50
        self.labelIndex = 0
        self.songLabel = []

        #Creates a path to the user's local Music directory
        self.music_directory_path = os.path.join(os.path.join(os.path.expanduser ("~"), "Music"), "Pufferfish_Music")

        #Creates a folder in the Windows music directory
        if not os.path.exists(self.music_directory_path): 
            os.makedirs(self.music_directory_path)

        # default settings dictionary
        self.DEFAULT_SETTINGS = {
            "visual_theme": "default",
            "account_info": {
                "username": None
            },
            "volume": 50,
            "preferences": {
                "language": "English",
                "notifications": True
            },
            "about_info": {
                "version": 0,
                "developer": False,
                # "Information about the app"
                },
            "Playlists": {"likedSongs":[]},
            "Directory":""
        }

        #frames
        self.frames["left"] = tkinter.Frame(self,bg = "#333333")
        self.frames["right"] = tkinter.Frame(self,bg = "#333333")
        self.frames["down"] = tkinter.Frame(self,bg = "#888888")
        
        #Load settings at the beginning of your program
        self.settingsLocation = os.path.join(os.getcwd(), 'settings.json')
        self.current_settings = self.load_settings()
        # Volume slider
        self.volume= tkinter.Scale(self.frames["down"], from_=0, to =100, orient="horizontal", command=self.setVolume, showvalue=0)

        # Access and update settings as needed
        self.visual_theme = self.current_settings["visual_theme"]
        # self.username = self.current_settings["account_info"]["username"]
        self.volume.set(self.current_settings["volume"])
        self.volume["label"] = f"Volume: {int(self.volume.get())}"
        # self.language = self.current_settings["preferences"]["language"]
        self.app_version = self.current_settings["about_info"]["version"]
        self.developer = self.current_settings["about_info"]["developer"]
        self.playlists = self.current_settings["Playlists"]
        self.directory = self.current_settings["Directory"]

        if not os.path.isdir(self.directory):
            self.directory = self.music_directory_path

        #self.directory = self.current_settings["Directory"]
        # the above line needs to be fixed so that it loads the directory and sets it and stuff

        #stylize the scrollbar with witchcraft and wizardry
        style=ttk.Style()
        style.theme_use('classic')
        style.configure("Vertical.TScrollbar", background="grey", bordercolor="black", arrowcolor="white")
        self.scrollbar = ttk.Scrollbar(self.frames["right"], orient="vertical")
        self.text = tkinter.Text(self.frames["right"],yscrollcommand=self.scrollbar.set,bg = "#aaaaaa",state="disabled")
        self.scrollbar.config(command=self.text.yview)
        #album default icon
        self.canvasAlbum = tkinter.Canvas(self.frames["left"],background="#333333")
        self.genAlbumIcon(2)

        self.buttonFactor = 0.4
        #prev button
        self.genPrevButton(self.buttonFactor)

        #play button
        self.genPausePlayButton(self.buttonFactor)

        #next button
        self.genNextButton(self.buttonFactor)

         #QueueListbox
        #self.createListbox()
        #Listbox buttons
        #self.buttonListbox()
        
        # seek bar
        self.seek= tkinter.Scale(self.frames["down"], from_=0, to =0, orient="horizontal", label="00:00", showvalue=0, command=self.moveSeek)
        self.seek.bind("<ButtonRelease-1>",self.seekTo)
        self.songQueued = {"id":None,"Title":None,"Artist":None,"Album":None,"Release":None, "Image":None, "Directory":None,"Length":0}
        self.mixer = pygame.mixer
        self.seekUpdater = self.updateSeek(self)
        self.seekUpdater.start()
        self.protocol("WM_DELETE_WINDOW",self.tidyDestroy)
        self.mixer.init()
        self.shuffle_dict = {}

        # Add a "Shuffle" button to your GUI
        self.shuffle_button = tkinter.Button(self.frames["down"], text="Enable Shuffle", command=self.toggleShuffle)
        self.shuffle_button.grid(row=0, column=4,sticky="nsew")

        #tag information stuff
        labelFont = font.nametofont("TkFixedFont")
        labelFont.configure(size=12,weight="bold")
        self.tagInfo = tkinter.Label(self.frames["down"],font=labelFont)
        #refresh to put everything in place

        #tab buttons
        self.tabButtons = tkinter.Frame(self.frames["right"])
        self.tabs = []
        self.tabs.append(tkinter.Button(self.tabButtons,text="Songs",command=partial(self.loadSongsIntoFrame,self.songs)))
        self.tabs.append(tkinter.Button(self.tabButtons,text="Playlists", command=self.loadPlaylistsIntoFrame))
        self.tabs.append(tkinter.Button(self.tabButtons,text="Search", command=self.loadSearchIntoFrame))

        self.loopButton = tkinter.Button(self.frames["down"],text="Enable Loop",command=self.toggleLoop)

        # Allows the user to select a directory and automatically update the list in the application
        def select_directory():
            # Configure file types to show in the dialog
            file_types = [("MP3 files", "*.mp3"), ("All files", "*.*")]

            # Ask the user to select a directory
            self.directory = filedialog.askdirectory()

            self.removeButtons()
            self.refresh() 

            self.current_settings["Directory"] = self.directory

            #self.ListboxRemoveOldSongs()
            self.loadSongs()
            self.loadSongsIntoFrame(self.songs)

            #self.ListboxHighlightPlaying()
            #self.Queue_listbox.selection_clear(0,tkinter.END)
            #self.currentSong = 0
           # self.Queue_listbox.selection_set(self.currentSong)

        #select directory button
        tkinter.Button(self.frames["down"], text = "Select Directory", command = select_directory).grid(row=0, column=3,sticky="nsew")
        
        # refresh to put everything in place
        self.refresh()
        self.loadSongs()
        #this bind ensures the songs are loaded into frame at the right size
        self.bind('<Visibility>',self.initLoadSongs)
        #self.refresh ()

        #there should be a set directory button for the whole application

        # Update the search results
        self.filtered_songs = []
        #self.update_search_results()

    #this function is called once the size of the window is rendered, then unbinds itself
    def initLoadSongs(self, event):
        if self.text.winfo_width() > 1 and self.text.winfo_height() > 1:
            self.loadSongsIntoFrame(self.songs)
            self.unbind('<Visibility>')

    #this loads the playlists into the window
    def loadPlaylistsIntoFrame(self):
        #code to clear the window of previous buttons
        self.text["state"] = "normal"
        self.removeButtons()
        self.songButtons.clear()
        #for loop for every playlist
        for i in self.playlists.keys():
            #dummy frame to hold the playlist button and potential delete playlist button
            dummyframe = tkinter.Frame()
            dummyframe.grid_columnconfigure(0,weight=1)
            dummyframe.grid_rowconfigure(0,weight=1)
            #this is the actual playlist button
            button = tkinter.Button(dummyframe,text=i,command=partial(self.loadSongsIntoFrame,self.playlists[i]))
            button.grid(row=0,column=0,sticky="nsew")
            #only allow delete button if it's not liked songs, that playlsit can't be deleted
            if button['text'] != "likedSongs":
                dummyframe.grid_columnconfigure(1,weight=1)
                deleteButton = tkinter.Button(dummyframe,text="Delete Playlist",command=partial(self.deletePlaylist,i))
                deleteButton.grid(row=0,column=1,sticky="nsew")
            #this is to set the size of the frame correctly
            dummyframe.grid_propagate(0)
            dummyframe["width"] = self.text.winfo_width()
            dummyframe["height"] = self.text.winfo_height()/20
            #this puts the frame in the correct palce on the window
            self.text.window_create("end",window=dummyframe)
            self.text.insert("end", "\n")
            self.songButtons.append(button)
        #all of this is for the add playlist button
        dummyframe = tkinter.Frame()
        dummyframe.grid_columnconfigure(0,weight=1)
        dummyframe.grid_rowconfigure(0,weight=1)
        button = tkinter.Button(dummyframe,text="New Playlist",command=partial(self.newPlaylist,self))
        button.grid(row=0,column=0,sticky="nsew")
        dummyframe.grid_propagate(0)
        dummyframe["width"] = self.text.winfo_width()
        dummyframe["height"] = self.text.winfo_height()/20
        self.text.window_create("end",window=dummyframe)
        self.text.insert("end", "\n")
        self.songButtons.append(button)
        #re disable the text box so that teh buttons can't be removed with a backspace
        self.text["state"] = "disabled"

    #function to delete playlists
    def deletePlaylist(self,name):
        self.playlists.pop(name)
        self.loadPlaylistsIntoFrame()

    #pop up window for making new playlists
    class newPlaylist(tkinter.Toplevel):
        def __init__(self, parent):
            super().__init__()
            self.title("Create a New Playlist")
            self.geometry("650x200")
            name = tkinter.Text(self,height=1) #please change this so it's not hardcoded a height
            name.grid(row=0,column=0)
            createButton = tkinter.Button(self,text="Create Playlist",command=partial(self.createPlaylist,name,parent))
            createButton.grid(row=1,column=0)

        #function to make a new playlist and add it to the internal dictionary
        def createPlaylist(self,name,parent):
            nameText = name.get(1.0,"end-1c")
            if nameText in list(parent.playlists.keys()):
                pass # error handle this eventually
            else:
                parent.playlists[nameText] = []
            parent.loadPlaylistsIntoFrame()
            self.destroy()

    #function to load search box into the window correctly
    def loadSearchIntoFrame(self):
        self.text["state"] = "normal"
        self.removeButtons()
        self.songButtons.clear()
        # Search bar and search button
        dummyFrame = tkinter.Frame()
        dummyFrame.grid_columnconfigure(0,weight=1)
        dummyFrame.grid_columnconfigure(1,weight=1)
        dummyFrame.grid_rowconfigure(1,weight=1)
        self.search_entry = tkinter.Entry(dummyFrame)
        self.search_entry.grid(row=0, column=0, sticky="nsew")
        self.search_button = tkinter.Button(dummyFrame, text="Search", command=self.search_song)
        self.search_button.grid(row=0, column=1,sticky="nsew")

        # Search results listbox
        self.search_results = tkinter.Listbox(dummyFrame, selectmode=tkinter.SINGLE)
        self.search_results.grid(row=1, column=0, columnspan=2,sticky="nsew")
        self.search_results.bind("<<ListboxSelect>>", self.select_song)
        dummyFrame.grid_propagate(0)
        dummyFrame["width"] = self.text.winfo_width()
        dummyFrame["height"] = self.text.winfo_height()
        self.text.window_create("end",window=dummyFrame)
        self.text["state"] = "disabled"

    def search_song(self):
        query = self.search_entry.get().strip().lower()
        if query:
            self.filtered_songs = [song for song in self.songs if query in song["Title"].lower() or query in song["Artist"].lower() or query in song["Album"].lower()]
        else:
            self.filtered_songs = self.songs
        self.update_search_results()

    def update_search_results(self):
        self.search_results.delete(0, tkinter.END)
        for song in self.filtered_songs:
            self.search_results.insert(tkinter.END, f"{song['Title']} - {song['Artist']}")

    def select_song(self, event):
        selected_index = self.search_results.curselection()
        if selected_index:
            selected_song = self.filtered_songs[int(selected_index[0])]
            self.queueSong(selected_song["id"])
    
    #this function just toggles the shuffle variable and button on/off
    def toggleShuffle(self):
        self.shuffle = not self.shuffle
        if self.shuffle: self.shuffle_button["text"] = "Disable Shuffle" 
        else: self.shuffle_button["text"] = "Enable Shuffle"

    #this function just toggles the loop variable and button on/off
    def toggleLoop(self):
        self.loop = not self.loop
        if self.loop: self.loopButton.config(text="Disable Loop")
        else: self.loopButton.config(text="Enable Loop")
          
    # give this a button
    def loadSongs(self):
        self.songs.clear()
        self.idCounter = 0
        #filepath = input("Enter filepath")

        if os.path.isdir(self.directory):
            os.chdir(self.directory)
              
            self.songs.clear()

            #this resets the imgs folder so that it's a fresh start
            if not os.path.exists("..\\imgs"): os.mkdir("..\\imgs")
            os.chdir("..\\imgs")
            for i in os.listdir():
                os.remove(str(os.getcwd()) + "\\" + str(i))

            os.chdir(self.directory)

            fileNames = os.listdir(self.directory) 

            if len(fileNames) == 0: 
                #needs error handling eventually
                print("Folder empty \n")
            else: 
                for i in range(len(fileNames)):
                    if fileNames[i].lower().endswith(".mp3"):
                        mp3 = eyed3.load(self.directory + "\\" + fileNames[i])

                        if mp3:
                            try:
                                if not mp3.tag.title:
                                    raise Exception("dummyExcept")
                                
                                trackTitle = mp3.tag.title
                            except:
                                trackTitle = fileNames[i].strip(".mp3")
                            try:
                                if not mp3.tag.artist:
                                    raise Exception("dummyExcept")
                                
                                trackArtist = mp3.tag.artist
                            except:
                                trackArtist = "Unknown"
                            try:
                                if not mp3.tag.album:
                                    raise Exception("dummyExcept")
                                trackAlbum = mp3.tag.album
                            except:
                                trackAlbum = "Unknown"
                            # try:
                            #     if not mp3.tag.getBestDate():
                            #         raise Exception("dummyExcept")
                                
                            #     trackRD = mp3.tag.getBestDate()
                            # except:
                            #     trackRD = "Unknown"
                            trackImage = False
                        else:
                            break
                            
                        try: 
                            trackTime = mp3.info.time_secs
                        except:
                            trackTime = 0

                        #this generates the imgs from the mp3s
                        try:
                            for image in mp3.tag.images:
                                image_file = open(f"..\\imgs\\{self.idCounter} - {trackTitle} - {trackArtist}().jpg","wb+")
                                image_file.write(image.image_data)
                                image_file.close()
                                trackImage = True
                        except:
                            trackImage = False
                            self.canvasAlbum.delete("all")
                            self.canvasAlbum.grid_remove()
                            self.canvasAlbum.grid(row=1,column=1)
                            self.genAlbumIcon(2)

                        #This append function prevents the program from loading mp3 files that have no image, because each ID in the array must include a value for trackImage
                        self.songs.append({"id":self.idCounter,"Title":trackTitle,"Artist":trackArtist,"Album":trackAlbum,"Image":trackImage,"Directory":self.directory+"//"+fileNames[i],"Length":trackTime})
                        for i in list(self.playlists.keys()):
                            for o in self.playlists[i]:
                                if o["Title"] == self.songs[-1]["Title"] and o["Artist"] == self.songs[-1]["Artist"] and o["Album"] == self.songs[-1]["Album"] and o["Length"] == self.songs[-1]["Length"]:
                                    o["id"] == self.songs[-1]["id"]
                        # print(mp3.info.time_secs, end = " | ")
                        #self.current_settings["likededSongs"]
                        self.idCounter += 1
                for i in list(self.playlists.keys()):
                    for o in self.playlists[i]:
                        if o not in self.songs:
                            o["id"] = -1
                #self.loadSongsIntoFrame(self.songs)       
        else:
            #needs error handling eventually
            print("File doesn't exist \n")
        # Load songs into the right frame without shuffling
        #self.loadSongsIntoFrame()

        # Queue the first song
        if self.songs:
            self.queueSong(self.songs[0]["id"])    

    # the pop up window that shows all the playlists you can add a song to, should eventually have a scrollbar and actually look good 
    class selectPlaylist(tkinter.Toplevel):
        def __init__(self, song, playlists):
            super().__init__()
            self.title("Select Playlist")
            self.geometry("300x200")
            for i in range(len(playlists.keys())):
                if song in playlists[list(playlists.keys())[i]]:
                    button = tkinter.Button(self,text="Remove from " + list(playlists.keys())[i])
                else:
                    button = tkinter.Button(self,text="Add to " + list(playlists.keys())[i])
                button.config(command=partial(self.toggleInPlaylist,playlists,song,button))
                button.grid(row=i,column=0)
        
        def toggleInPlaylist(self,playlists,song,button):
            if "Remove from " in button["text"] and song in playlists[button["text"].replace("Remove from ","")]:
                playlists[button["text"].replace("Remove from ","")].remove(song)
                button["text"] = "Add to " + button["text"].replace("Remove from ","")
            elif "Add to " in button["text"]:
                playlists[button["text"].replace("Add to ","")].append(song)
                button["text"] = "Remove from " + button["text"].replace("Add to ","")


    #loads songs into the right frame tkinter frame
    def loadSongsIntoFrame(self,songlist = []):
        self.text["state"] = "normal"
        self.removeButtons()
        self.songButtons.clear()
        for i in range(len(songlist)):
            dummyframe = tkinter.Frame()
            dummyframe.grid_columnconfigure(0,weight=1)
            dummyframe.grid_columnconfigure(1,weight=0)
            dummyframe.grid_rowconfigure(0,weight=1)
            playlistButton = tkinter.Button(dummyframe,text="Add to Playlist",command=partial(self.selectPlaylist,songlist[i],self.playlists))
            button = tkinter.Button(dummyframe,text=f" {songlist[i]['Title']} | {songlist[i]['Artist']} | {songlist[i]['Album']}", anchor="w", command=partial(self.queueSong, songlist[i]["id"]), bg="white", activebackground="grey", fg="black", width=(dummyframe.winfo_width()-playlistButton.winfo_width()))
            if songlist[i] not in self.songs:
                button["state"] = "disabled"
            button.grid(row=0,column=0,sticky="nsew")
            playlistButton.grid(row=0,column=1,sticky="nse")
            dummyframe.grid_propagate(0)
            dummyframe["width"] = self.text.winfo_width()
            # dummyframe["width"] = self.frames["right"].winfo_width()
            dummyframe["height"] = self.text.winfo_height()/20
            self.text.window_create("end", window=dummyframe)
            if (i < len(songlist) - 1):
                self.text.insert("end", "\n")

            # Append the button to the songButtons array
            self.songButtons.append(button)
        self.text["state"] = "disabled"

        #self.songs = [song for song in self.songs if song in self.favorites]

    def removeButtons(self):
        self.text.delete(1.0,"end")
        self.songButtons = []
        # pass

    #queues and plays the selected song
    def queueSong(self,id):
        for i in range(len(self.songs)):
            if self.songs[i]["id"] == id:
                self.songQueued = self.songs[i]

        #verifies the song exists and was loaded
        if not self.songQueued["id"] == None:
            self.songInfo = f"{self.songQueued['Title']}   |   {self.songQueued['Artist']}   |   {self.songQueued['Album']}"

            #resets and fills the left frame's canvas with the album cover
            self.canvasAlbum.delete("all")
            self.canvasAlbum.grid_remove()
            if self.songQueued["Image"]:
                # self.canvasAlbum.pack(side = "left", fill = "both", expand = True ,padx=2,pady=2)
                self.canvasAlbum.config(width=640,height=640)
                self.canvasAlbum.grid(row=0, column=0, rowspan=3, columnspan=3)
                self.albumimg = ImageTk.PhotoImage(Image.open(f"..\\imgs\\{self.songQueued['id']} - {self.songQueued['Title']} - {self.songQueued['Artist']}().jpg"))
                self.canvasAlbum.create_image(0, 0, anchor="nw", image=self.albumimg)
            else:
                self.genAlbumIcon(2)
                self.canvasAlbum.grid(row=1, column=1, rowspan=1, columnspan=1)
            #gives the seek abr the right length
            self.seek.config(to=self.songQueued["Length"])
            #sets the seek bar back to 0
            self.seek.set(0)
            #displays information about the currently playing track
            self.tagInfo.config(width=20, text=self.songInfo)
            self.scroll_text
            self.seek.config(label="00:00")
            #For Testing purposes
            #print("THE DIRECTORY IS ", self.songQueued["Directory"]) 
            #loads and then plays the selected song
            self.mixer.music.load(self.songQueued["Directory"])
            self.mixer.music.play()
            if self.paused: self.pause()
            #self.loadIntoListbox()

    def scroll_text(self):
        self.labelIndex += 1
        songLabel = [self.songInfo]
        if self.labelIndex >= len(self.songInfo):
            self.labelIndex = 0
        self.tagInfo.config(width=20, text=songLabel[self.labelIndex:]+songLabel[:self.labelIndex])

    # load settings from the JSON file
    def load_settings(self):
        try:
            with open(self.settingsLocation, 'r') as file:
                print("uh-huh")
                settings = json.load(file)
                file.close()
        except FileNotFoundError:
            print("uh-oh!")
            settings = self.DEFAULT_SETTINGS
            # settingsFile = os.path.join (self.music_directory_path, "settings.json")
            with open(os.path.join(self.settingsLocation), 'w+') as file:
                json.dump(self.DEFAULT_SETTINGS, file)

        return settings

    #a thread to update the seek bar every second
    class updateSeek(threading.Thread):
        def __init__(self,parent):
            super().__init__()
            self.parent = parent
            self._stop = threading.Event()
            self.daemon = True

        def run(self):
            while not self._stop.is_set():
                if not self.parent.seek.get() == self.parent.songQueued["Length"] and not self.parent.paused:
                    self.parent.seek.set(self.parent.seek.get() + 1)
                    time.sleep(1)
            return
        
    # a fresh function for all of the elements on the page (tkinter thing)
    def refresh(self):
        for i in range(len(self.frames)):
            self.frames[list(self.frames)[i]].grid_remove()

        #frames
        for i in range(6):
            self.rowconfigure(i,weight=1, uniform='row')
        for i in range(2):
            self.columnconfigure(i,weight=1,uniform='column')
        self.frames["left"].grid(row=0, column=0, padx=1, pady=1,sticky="nsew",rowspan=5)
        self.frames["left"].grid_rowconfigure(0, weight=1)
        self.frames["left"].grid_columnconfigure(0, weight=1)
        self.frames["left"].grid_rowconfigure(1, weight=1)
        self.frames["left"].grid_columnconfigure(1, weight=1)
        self.frames["left"].grid_rowconfigure(2, weight=1)
        self.frames["left"].grid_columnconfigure(2, weight=1)
        self.frames["right"].grid(row=0, column=1, sticky="nsew",rowspan=5)
        self.frames["right"].grid_rowconfigure(1, weight=1)
        self.frames["right"].grid_columnconfigure(0, weight=1)
        self.frames["down"].grid(row=5, column=0, rowspan=1,columnspan=2, sticky="nsew")
        for i in range(6):
            self.frames["down"].grid_columnconfigure(i, weight=1,uniform="column")
        for i in range(2):
            self.frames["down"].grid_rowconfigure(i, weight=1)

        self.text.grid(row=1,column=0,sticky="nsew",pady=(0,20))
        self.scrollbar.grid(row=1,column=1,sticky="nsew")

        #tag info
        self.tagInfo.grid(row=1,column=0,columnspan=3,sticky="nsew")

        #Images
        self.refreshCanvases()

        #seek bar
        self.seek.grid(row=1, column=3,columnspan=2,sticky="nsew")
        
        #volume slider
        self.volume.grid(row=1, column=5,columnspan=2,sticky="nsew")
        self.loopButton.grid(row=0,column=5,sticky="nsew")

        self.tabButtons.grid(row=0,column=0,columnspan=2,sticky="nsew")
        self.tabButtons.grid_rowconfigure(0,weight=1)
        for i in range(len(self.tabs)):
            self.tabButtons.grid_columnconfigure(i,weight=1)
            self.tabs[i].grid(row=0,column=i,sticky="nsew")

        #makes all of the frames expand to fit the window
        #parent window
        for i in range(self.grid_size()[0]):
            self.grid_columnconfigure(i,weight=1)
        for i in range(self.grid_size()[1]):
            self.grid_rowconfigure(i,weight=1)

    def resize_event(self, event):
        width = event.width
        height = event.height

        # Ensure the "left" frame is always a square
        size = min(width, height)
        self.frames["left"].config(width=size, height=size)
        self.frames["left"].update_idletasks()  # Force update

    # a refresh for only the canvases (buttons and album cover)
    def refreshCanvases(self):
        self.canvasAlbum.grid_remove()
        for i in range(len(self.canvases)):
            self.canvases[list(self.canvases)[i]].grid_remove()
        
        self.canvasAlbum.grid(row=1,column=1)
        for i in range(len(self.canvases)):
            self.canvases[list(self.canvases)[i]].grid(row=0,column=i,sticky="nsew")

    #generates the play/pause button image
    def genPausePlayButton(self,factor):
        self.canvases["play"] = tkinter.Canvas(self.frames["down"],width=100*factor,height=100*factor,background="SystemButtonFace",borderwidth=2,relief="raised")
        self.canvases["play"].create_oval(10*factor,10*factor,97*factor,97*factor, outline="black", fill="white", width=2)
        self.canvases["play"].create_polygon([40*factor,25*factor,80*factor,50*factor,40*factor,80*factor],outline="black",fill="white",width=2)
        #the function for clicking on the play button
        def onClick(event):
            event.widget.configure(relief="sunken")
            event.widget.delete("all")
            if self.paused:
                event.widget.create_oval(10*factor+2,10*factor+2,97*factor+2,97*factor+2, outline="black", fill="white", width=2)
                event.widget.create_polygon([40*factor+2,25*factor+2,80*factor+2,50*factor+2,40*factor+2,80*factor+2],outline="black",fill="white",width=2)
            else:
                event.widget.create_rectangle(23*factor+2,10*factor+2,43*factor+2,95*factor+2, outline="black", fill="white", width=2)
                event.widget.create_rectangle(65*factor+2,10*factor+2,85*factor+2,95*factor+2, outline="black", fill="white", width=2)
        self.canvases["play"].bind("<ButtonPress-1>",onClick)
        #the function for releasing the play button (actually plays)
        def onRelease(event):
            event.widget.configure(relief="raised")
            event.widget.delete("all")
            if not self.paused:
                event.widget.create_oval(10*factor,10*factor,97*factor,97*factor, outline="black", fill="white", width=2)
                event.widget.create_polygon([40*factor,25*factor,80*factor,50*factor,40*factor,80*factor],outline="black",fill="white",width=2)
                self.pause()
            else:
                event.widget.create_rectangle(23*factor,10*factor,43*factor,95*factor, outline="black", fill="white", width=2)
                event.widget.create_rectangle(65*factor,10*factor,85*factor,95*factor, outline="black", fill="white", width=2)
                self.play()
        self.canvases["play"].bind("<ButtonRelease-1>",onRelease)

    #generates the next button
    def genNextButton(self,factor):
        self.canvases["next"] = tkinter.Canvas(self.frames["down"],width=100*factor,height=100*factor,background="SystemButtonFace",borderwidth=2,relief="raised")
        self.canvases["next"].create_polygon([20*factor,25*factor,60*factor,50*factor,20*factor,80*factor],outline="black",fill="white",width=2)
        self.canvases["next"].create_rectangle(75*factor,25*factor,85*factor,80*factor,outline="black",fill="white",width=2)
        #function for clicking the next button
        def onClick(event):
            event.widget.configure(relief="sunken")
            event.widget.delete("all")
            event.widget.create_polygon([20*factor+2,25*factor+2,60*factor+2,50*factor+2,20*factor+2,80*factor+2],outline="black",fill="white",width=2)
            event.widget.create_rectangle(75*factor+2,25*factor+2,85*factor+2,80*factor+2,outline="black",fill="white",width=2)
        self.canvases["next"].bind("<ButtonPress-1>",onClick)
        #function for releasing the next button (actually moves to the next song)
        def onRelease(event):
            event.widget.configure(relief="raised")
            event.widget.delete("all")
            event.widget.create_polygon([20*factor,25*factor,60*factor,50*factor,20*factor,80*factor],outline="black",fill="white",width=2)
            event.widget.create_rectangle(75*factor,25*factor,85*factor,80*factor,outline="black",fill="white",width=2)
            self.moveSong(1)
            # self.Queue_listbox.selection_clear(0,tkinter.END)
            #self.currentSong += 1
            #self.Queue_listbox.selection_set(self.currentSong)
            #self.ListboxHighlightPlaying()
        self.canvases["next"].bind("<ButtonRelease-1>",onRelease)

    #generates the previous button
    def genPrevButton(self,factor):
        self.canvases["prev"] = tkinter.Canvas(self.frames["down"],width=100*factor,height=100*factor,background="SystemButtonFace",borderwidth=2,relief="raised")
        self.canvases["prev"].create_polygon([85*factor,25*factor,45*factor,50*factor,85*factor,80*factor],outline="black",fill="white",width=2)
        self.canvases["prev"].create_rectangle(20*factor,25*factor,30*factor,80*factor,outline="black",fill="white",width=2)
        #self.canvases["prev"].grid(row=0,column=0)
        #function for pressing the previous button
        def onClick(event):
            event.widget.configure(relief="sunken")
            event.widget.delete("all")
            event.widget.create_polygon([85*factor+2,25*factor+2,45*factor+2,50*factor+2,85*factor+2,80*factor+2],outline="black",fill="white",width=2)
            event.widget.create_rectangle(20*factor+2,25*factor+2,30*factor+2,80*factor+2,outline="black",fill="white",width=2)
        self.canvases["prev"].bind("<ButtonPress-1>",onClick)
        #function for releasing the previous button (actually moves to the previous song)
        def onRelease(event):
            event.widget.configure(relief="raised")
            event.widget.delete("all")
            event.widget.create_polygon([85*factor,25*factor,45*factor,50*factor,85*factor,80*factor],outline="black",fill="white",width=2)
            event.widget.create_rectangle(20*factor,25*factor,30*factor,80*factor,outline="black",fill="white",width=2)

            if (self.seek.get() <= 5):
                self.moveSong(-1)
                #self.ListboxHighlightPlaying()
               # self.Queue_listbox.selection_clear(0,tkinter.END)
               # self.currentSong -= 1
               # self.Queue_listbox.selection_set(self.currentSong)
            else:
                self.seek.set(0)
                self.mixer.music.set_pos(self.seek.get())

        self.canvases["prev"].bind("<ButtonRelease-1>",onRelease)
    
    #generates the default album icon for a placeholder on startup
    def genAlbumIcon(self,factor):
        self.canvasAlbum.config(width=100*factor,height=100*factor)
        self.canvasAlbum.create_oval(35*factor,20*factor,65*factor,50*factor,outline="black",fill="white",width=2)
        self.canvasAlbum.create_polygon([30*factor,60*factor,70*factor,60*factor,80*factor,70*factor,80*factor,80*factor,20*factor,80*factor,20*factor,70*factor,30*factor,60*factor],outline="black",fill="white",width=2)

    #play function
    def play(self):
        self.mixer.music.unpause()
        self.paused = False

    #pause function
    def pause(self):
        self.mixer.music.pause()
        self.paused = True

    #seeking function to move the song to reflect the time shown on the seek bar
    def seekTo(self,event):
        #logic to handle if it's paused or not nad if it's playing or not
        self.seek.config(label=f"{int(self.seek.get() / 60):02d}:{int((float(self.seek.get() / 60) - int(self.seek.get() / 60)) * 60 ):02d}")
        if not self.mixer.music.get_busy() and not self.paused:
            self.mixer.music.play()
            self.mixer.music.set_pos(self.seek.get())
        else:
            self.mixer.music.set_pos(self.seek.get())

    #the volume setting function for the volume slider
    def setVolume(self,event):
        self.mixer.music.set_volume(self.volume.get()/100)
        self.volume["label"] = f"Volume: {int(self.volume.get())}"
        self.current_settings["volume"] = self.volume.get()

    #the is run on the X being clicked so that the threads are properly shut down with the window
    def tidyDestroy(self):
        # save the settings to the json file
        self.current_settings["Playlists"] = self.playlists
        with open(self.settingsLocation, 'w+') as file:
            try:
                # print(self.current_settings["Directory"])
                # print(self.current_settings)
                json.dump(self.current_settings, file)
                file.close()
                # print(self.current_settings["Directory"])
                print("Settings updated successfully.")
            except Exception as e:
                print("Error:", e)
        self.seekUpdater._stop.set
        time.sleep(1)
        self.destroy()

    #this is the function for the next and previous buttons
    def moveSong(self,direction):
        if self.loop:
            self.queueSong(self.songQueued["id"])
            return
        currentSong = self.songQueued
        if self.shuffle:
            self.queueSong(self.songs[random.randint(0,len(self.songs)-1)]["id"])
            return
        for index, song in enumerate(self.songs):
            if song["id"]== currentSong["id"]:
                break
        #index is where the self.songQueued = the currentSong
        if direction == -1:
            if index == 0:
                self.queueSong(self.songs[len(self.songs)-1]["id"])
            else:
                self.queueSong(self.songs[index-1]["id"])
        elif direction == 1:
            if index == len(self.songs)-1:
                self.queueSong(self.songs[0]["id"])
            else:
                self.queueSong(self.songs[index + 1]["id"])
        #old function
        #if -1 < self.songQueued["id"] + direction < len(self.songs):
         #   self.queueSong(self.songs[self.songQueued["id"] + direction]["id"])
    # This is code I tried to add  
          
      #  elif self.songQueued["id"] + direction <= -1:
       #     self.queueSong(self.songs[len(self.songs)-1]["id"])
       # elif self.songQueued["id"] + direction > len(self.songs)-1:
       #     self.queueSong(self.songs[0]["id"])
    
#     # This is the function for the next and previous buttons
#     def moveSong(self, direction):
#         if self.favorites_mode:
#             current_index = self.get_favorite_index(self.songQueued["id"])
#             if current_index is not None:
#                 new_index = (current_index + direction) % len(self.favorites)
#                 new_song_id = self.favorites[new_index]["id"]
#                 self.queueSong(new_song_id)
                
#             else:
#                 pass  
#         else:
#             new_index = (self.songQueued["id"] + direction) % len(self.songs)
#             self.queueSong(self.songs[new_index]["id"])  
    def moveSeek(self, event):
        self.seek.config(label=f"{int(self.seek.get() / 60):02d}:{int((float(self.seek.get() / 60) - int(self.seek.get() / 60)) * 60 ):02d}")
        if self.seek.get() == int(self.songQueued["Length"]) and not self.paused:
            self.moveSong(1)
            #self.ListboxHighlightPlaying()
          #  self.Queue_listbox.selection_clear(0,tkinter.END)
            #self.currentSong += 1
          #  self.Queue_listbox.selection_set(self.currentSong)

    # def createListbox(self):
    #     self.listbox_scrollbar = tkinter.Scrollbar(self.frames["down"],orient = "vertical")
    #     self.Queue_listbox = tkinter.Listbox(self.frames["down"], bg = "white", yscrollcommand=self.listbox_scrollbar.set)   
    #    # self.Queue_listbox.insert(tkinter.END, "SongQueue")
    #     self.Queue_listbox.config(yscrollcommand=self.listbox_scrollbar.set)        
    #     self.listbox_scrollbar.config(command=self.Queue_listbox.yview)
    #     self.Queue_listbox.grid(row=2, column =3,rowspan=2, sticky ="nsew") 
    #     self.listbox_scrollbar.grid(row=2, column=4,rowspan=2,sticky="nsw")   

    # def loadIntoListbox(self):
    #     #Populates the listbox 
    #     listbox_items = self.Queue_listbox.get(0,tkinter.END)
    #     for song in self.songs:
    #         song_key = f"{song['id']}: {song['Title']}-{song['Artist']}"
    #         if song_key not in listbox_items:
    #            self.Queue_listbox.insert(tkinter.END,song_key)
               

    # def buttonListbox(self):
    #  # made the buttons show up 
    #  self.btnAddToListbox =  tkinter.Button(self.frames["down"], text = "Add",bg="SystemButtonFace", activebackground="Black", fg="Black", command = self.addSong).grid(row=2, column=4)
    #  self.btnDeleteToListbox =  tkinter.Button(self.frames["down"], text = "Delete",bg="SystemButtonFace", activebackground="Black", fg="Black", command = self.deleteSong).grid(row=3, column=4)
    #  self.btnUpToListbox = tkinter.Button(self.frames["down"], text = "↑",bg="SystemButtonFace", activebackground="Black", fg="Black",command = self.upListbox).grid(row=2, column=2, sticky="nes")
    #  self.btnDownToListbox = tkinter.Button(self.frames["down"], text = "↓",bg="SystemButtonFace", activebackground="Black", fg="Black",command = self.downListBox).grid(row=3, column=2, sticky="nes")
    #  self.grid_columnconfigure(0,weight=1)
    #  self.grid_rowconfigure(1,weight=0)
    #  self.grid_rowconfigure(2,weight=1)
    #  #Click  
    # # def myClick(self):
    # #     self.btnAddToListbox = tkinter.Label(self.frames["down"], text = "Add",bg="SystemButtonFace", activebackground="Black", fg="Black").grid(row=1, column=5)
    # # def myRelease(self):
    # def addSong(self):
    #     #this function needs some work
    #     # put the selected song into the queue
    #     file_path = filedialog.askopenfilename()

    #     #need to change file_path to be ID
    #     #file Selector
    #     #FileName Change
    #     #self.queueSong(file_path)
    #     i = file_path
    #     #For testing purposes
    #     #print("THIS IS THE FILEPATH",file_path)
    #     if i.lower().endswith(".mp3"):
    #         mp3 = eyed3.load(file_path)

    #         if mp3:
    #             trackTitle = mp3.tag.title
    #             trackArtist = mp3.tag.artist
    #             trackAlbum = mp3.tag.album
    #             trackRD = mp3.tag.getBestDate()
    #             trackImage = False
    #         else:
    #             print("Error loading MP3")

    #         try: 
    #             trackTime = mp3.info.time_secs
    #         except:
    #             trackTime = 0

    #         #this generates the imgs from the mp3s
    #         if mp3.tag.images:
    #             for image in mp3.tag.images:
    #                 image_file = open(f"..\\imgs\\{self.idCounter} - {trackTitle} - {trackArtist}().jpg","wb+")
    #                 image_file.write(image.image_data)
    #                 image_file.close()
    #                 trackImage = True
    #         else:
    #             self.canvasAlbum.delete("all")
    #             self.canvasAlbum.grid_remove()
    #             self.canvasAlbum.grid(row=1,column=1)
    #             # self.canvasAlbum.pack(side = "left", fill = "both", expand = True ,padx=2,pady=2)
    #             self.genAlbumIcon(2)
    #             trackImage = False
    #         # doesn't have error handling

    #         #This append function prevents the program from loading mp3 files that have no image, because each ID in the array must include a value for trackImage # self directory used to be just i
    #     self.songs.append({"id":self.idCounter,"Title":trackTitle,"Artist":trackArtist,"Album":trackAlbum,"Release":trackRD,"Image":trackImage,"Directory":i,"Length":trackTime})
    #         # print(mp3.info.time_secs, end = " | ")
    #     self.idCounter += 1
    #     #Get the last added song's index (assumming 0-based indexing)
    #     new_song_index = len(self.songs) - 1
  
    #     #if you just clear it just going to add up
    #     #same list initiially loads on runtime
    #     #find a way to clear self.songs and add to queue
    #     #make a new Queue
    #     song_key = f"{self.songs[new_song_index]['id']}: {self.songs[new_song_index]['Title']}-{self.songs[new_song_index]['Artist']}"
    #     self.Queue_listbox.insert(tkinter.END,song_key)
    #     #add song adjust to song currently being played

    # def deleteSong(self):
    #     current = self.Queue_listbox.curselection() 
    #     current = int(current[0])# convert to int

    #     if 0 <= current <= self.Queue_listbox.size():
    #         item_text = self.Queue_listbox.get(current)
    #         self.Queue_listbox.delete(current)

    #     targetId = item_text[0].split(":",1)[0]
        
    #     for song in self.songs:
         
    #         if str(song["id"]) == targetId:
    #             self.songs.remove(song)
    #            # Prints the song removed for testing/ info
    #            # print(self.songs)

    # def upListbox(self):
    #     current = self.Queue_listbox.curselection() 

    #     if not current:#check if there is a selection
    #         return

    #     current = int(current[0])# convert to int

    #     if current == 0: # check to see if song already at top
    #         return 
    #     if 0 < current <= self.Queue_listbox.size():
    #         item_text = self.Queue_listbox.get(current)
    #         self.Queue_listbox.delete(current)
    #     insert_index = current - 1 

    #     if insert_index < 0:# position 1 is the first songs
    #         insert_index = 0

    #     self.Queue_listbox.insert(insert_index,item_text)
       
    #     #take text we have split it whereever we see a collun
    #     # take the first half of it
    #     targetId = item_text[0].split(":",1)[0]
        
    #     for song in self.songs:
         
    #         if str(song["id"]) == targetId:
    #             self.songs.remove(song)
    #             self.songs.insert(insert_index,song)


    # def downListBox(self):
    #     current = self.Queue_listbox.curselection() 

    #     if not current:#check if there is a selection
    #         return

    #     current = int(current[0])# convert to int

    #     if 0 <= current <= self.Queue_listbox.size():
    #         item_text = self.Queue_listbox.get(current)
    #         self.Queue_listbox.delete(current)
    #     insert_index = current + 1 

    #     if insert_index == self.Queue_listbox.size() -1: # position 1 is the first songs
    #         insert_index = self.Queue_listbox.size() -1

    #     self.Queue_listbox.insert(insert_index,item_text)
       
    #     #take text we have split it where ever we see a collun
    #     # take the first half of it
    #     targetId = item_text[0].split(":",1)[0]
        
    #     for song in self.songs:
         
    #         if str(song["id"]) == targetId:
    #             self.songs.remove(song)
    #             self.songs.insert(insert_index,song)

    # def ListboxRemoveOldSongs(self):
    #     for song in self.songs:
    #         self.Queue_listbox.delete(0)

    # def ListboxHighlightPlaying(self):

    #     currentSong = self.songQueued
        
    #     for index, song in enumerate(self.songs):
    #         # for Testing
    #         #print("THE CURRENT SONG",song) 
    #         #print("THE current index is",index)
    #         if song["id"]== currentSong["id"]:
    #             self.Queue_listbox.selection_clear(0,tkinter.END)
    #             self.Queue_listbox.selection_set(index)
    #             break

# this runs the whole file
Window().mainloop()