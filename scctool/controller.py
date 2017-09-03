#!/usr/bin/env python
import logging

# create logger
module_logger = logging.getLogger('scctool.controller')

try:
    from scctool.matchdata import *
    from scctool.apithread import *
    from scctool.webapp import *
    from scctool.settings import *
    from scctool.ftpuploader import *
    from scctool.obs import *
    import scctool.settings
    import scctool.twitch
    import scctool.nightbot
    import scctool.obs
    import webbrowser
    import base64
    
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import QCompleter
    
    
except Exception as e:
    module_logger.exception("message") 
    raise  

class MainController:
    
    def __init__(self):
        try:
            self.matchData = matchData()
            self.SC2ApiThread = SC2ApiThread(self)
            self.checkVersionThread = CheckVersionThread(self,scctool.settings.versioncontrol)
            self.webApp = FlaskThread()
            self.webApp.signal_twitch.connect(self.webAppDone_twitch)
            self.webApp.signal_nightbot.connect(self.webAppDone_nightbot)
            self.ftpUploader = FTPUploader()
            self.websocketThread = WebsocketThread()
            self.placeholderSetup()
            self._warning = False
            
        except Exception as e:
            module_logger.exception("message")

    def placeholderSetup(self):
        
        self.placeholders = PlaceholderList()
        self.placeholders.addConnection("Team1", lambda: self.matchData.getTeam(0))
        self.placeholders.addConnection("Team2", lambda: self.matchData.getTeam(1))
        self.placeholders.addConnection("URL", self.matchData.getURL)
        self.placeholders.addConnection("BestOf", lambda: str(self.matchData.getBestOfRaw()))
        self.placeholders.addConnection("League", self.matchData.getLeague)
        self.placeholders.addConnection("Score", self.matchData.getScoreString)
            
            
    def setView(self,view):
        self.view = view
        try:
            self.matchData.readJsonFile()
            self.view.trigger = False
            self.updateForms()
            self.view.trigger = True
            self.setCBs()
            self.view.resizeWindow()
        except Exception as e:
            module_logger.exception("message")    

    def updateForms(self):
        try:
            if(self.matchData.getProvider() == "Custom"):
                self.view.tabs.setCurrentIndex(1) 
            else:
                self.view.tabs.setCurrentIndex(0) 
                
            self.view.cb_allkill.setChecked(self.matchData.getAllKill())
            
            index = self.view.cb_bestof.findText(str(self.matchData.getBestOfRaw()),\
                                                                Qt.MatchFixedString)
            if index >= 0:                                   
               self.view.cb_bestof.setCurrentIndex(index)
               
            index = self.view.cb_minSets.findText(str(self.matchData.getMinSets()),\
                                                                Qt.MatchFixedString)
            if index >= 0:                                   
               self.view.cb_minSets.setCurrentIndex(index)
            
            self.view.le_url.setText(self.matchData.getURL())
            self.view.le_url_custom.setText(self.matchData.getURL())
            self.view.le_league.setText(self.matchData.getLeague())
            self.view.sl_team.setValue(self.matchData.getMyTeam())
            for i in range(2):
                self.view.le_team[i].setText(self.matchData.getTeam(i))
                
            for i in range(min(self.view.max_no_sets,self.matchData.getNoSets())):
                for j in range(2):
                    self.view.le_player[j][i].setText(self.matchData.getPlayer(j,i))
                    self.view.cb_race[j][i].setCurrentIndex(scctool.settings.race2idx(self.matchData.getRace(j,i)))

                self.view.le_map[i].setText(self.matchData.getMap(i))

                self.view.sl_score[i].setValue(self.matchData.getMapScore(i))
                
            for i in range(self.matchData.getNoSets(),self.view.max_no_sets): 
                for j in range(2):
                    self.view.le_player[j][i].hide()
                    self.view.cb_race[j][i].hide()
                self.view.le_map[i].hide()    
                self.view.sl_score[i].hide()
                self.view.label_set[i].hide()
                
            for i in range(min(self.view.max_no_sets,self.matchData.getNoSets())):
                for j in range(2):
                    self.view.le_player[j][i].show()
                    self.view.cb_race[j][i].show()
                self.view.le_map[i].show()    
                self.view.sl_score[i].show()
                self.view.label_set[i].show()

        except Exception as e:
            module_logger.exception("message")  
            raise  
                
    def updateLogos(self):
        pixmap = QIcon(self.linkFile(scctool.settings.OBSdataDir+'/logo1'))
        self.view.qb_logo1.setIcon(pixmap)
        
        pixmap = QIcon(self.linkFile(scctool.settings.OBSdataDir+'/logo2'))
        self.view.qb_logo2.setIcon(pixmap)
        
        self.updateLogosHTML()

                
    def updateData(self):     
        try:
            self.matchData.setMyTeam(self.view.sl_team.value())
            self.matchData.setLeague(self.view.le_league.text())

            for i in range(2):
                 self.matchData.setTeam(i, self.view.le_team[i].text())
                
            for i in range(min(self.view.max_no_sets, self.matchData.getNoSets())):
                for j in range(2):
                     self.matchData.setPlayer(j, i,self.view.le_player[j][i].text())
                     self.matchData.setRace(j ,i,scctool.settings.idx2race(self.view.cb_race[j][i].currentIndex()))
                
                self.matchData.setMap(i, self.view.le_map[i].text())
                print(self.view.le_map[i].text())
                self.matchData.setMapScore(i, self.view.sl_score[i].value(),True)
                
        except Exception as e:
            module_logger.exception("message")    
                    
    def applyCustom(self, bestof, allkill, minSets, url):  
        msg = ''
        try: 
        
            self.matchData.setCustom(bestof, allkill)
            self.matchData.setMinSets(minSets)
            self.matchData.setURL(url)
            self.matchData.writeJsonFile()
            self.updateForms()
            self.view.resizeWindow()
            self.updateOBS()
            
        except Exception as e:
            msg = str(e)
            module_logger.exception("message")    
          
        return msg
        
    def resetData(self):  
        msg = ''
        try: 
        
            self.matchData.resetData()
            self.matchData.writeJsonFile()
            self.updateForms()
            self.updateOBS()
            
        except Exception as e:
            msg = str(e)
            module_logger.exception("message")    
          
        return msg
                    
    def refreshData(self,url):      
        msg = ''
        try:
            self.matchData.parseURL(url)
            self.matchData.grabData()
            self.matchData.autoSetMyTeam()
            self.matchData.writeJsonFile()
            try:
                self.matchData.downloadLogos(self)
                self.matchData.downloadMatchBanner(self)
            except:
                pass
            self.updateLogos()
            self.updateForms()  
            self.view.resizeWindow()
        except Exception as e:
            msg = str(e)
            module_logger.exception("message")    
          
        return msg
        
    def setCBs(self):
        try:
            if(scctool.settings.CB_ScoreUpdate):
                self.view.cb_autoUpdate.setChecked(True)
                
            if(scctool.settings.CB_ToggleScore):
                self.view.cb_autoToggleScore.setChecked(True)
                
            if(scctool.settings.CB_ToggleProd):
                self.view.cb_autoToggleProduction.setChecked(True)
                
            if(scctool.settings.CB_PlayerIntros):
                self.view.cb_playerIntros.setChecked(True) 
                
            self.view.cb_autoFTP.setChecked(scctool.settings.Config.getboolean("FTP","upload"))
        except Exception as e:
            module_logger.exception("message")    

    def updateOBS(self):
        try:
            self.updateData()
            self.matchData.updateMapIcons(self)
            self.matchData.updateScoreIcon(self)
            self.matchData.createOBStxtFiles(self)
            self.matchData.updateLeagueIcon(self)
            self.matchData.writeJsonFile()
            self.matchData.resetChanged()
        except Exception as e:
            module_logger.exception("message")  
      
    def allkillUpdate(self):
        
        self.updateData()
        if(self.matchData.allkillUpdate()):
            self.updateForms()
    
    def webAppDone_nightbot(self):
        try:
            self.view.mysubwindow1.nightbotToken.setTextMonitored(FlaskThread._single.token_nightbot)
            
            self.view.raise_()
            self.view.show()
            self.view.activateWindow()
            
            
            self.view.mysubwindow1.raise_()
            self.view.mysubwindow1.show()
            self.view.mysubwindow1.activateWindow()
            
        except Exception as e:
            module_logger.exception("message")  
            
    def webAppDone_twitch(self):
        try:
            self.view.mysubwindow1.twitchToken.setTextMonitored(FlaskThread._single.token_twitch)
            
            self.view.raise_()
            self.view.show()
            self.view.activateWindow()
            
            
            self.view.mysubwindow1.raise_()
            self.view.mysubwindow1.show()
            self.view.mysubwindow1.activateWindow()
            
        except Exception as e:
            module_logger.exception("message")              
            
    def getNightbotToken(self):
        try:
            self.webApp.start()
            webbrowser.open("http://localhost:65010/nightbot")
        except Exception as e:
            module_logger.exception("message")  
       
    def getTwitchToken(self):
        try:
            self.webApp.start()
            webbrowser.open("http://localhost:65010/twitch")
        except Exception as e:
            module_logger.exception("message")         
        
    def updateNightbotCommand(self):
        try:
            msg = ''
            self.updateData()
            message = scctool.settings.Config.get("NightBot","message")
            message = self.placeholders.replace(message)
            msg = scctool.nightbot.updateCommand(message)
        except Exception as e:
            msg = str(e)
            module_logger.exception("message") 
            pass 
            
        return msg    
            
        
    def updateTwitchTitle(self):
        try:
            msg = ''
            self.updateData()
            try:
                title = scctool.settings.Config.get("Twitch","title_template")
                title = self.placeholders.replace(title)
                msg = scctool.twitch.updateTitle(title)
            except Exception as e:
                msg = str(e)
                module_logger.exception("message") 
                pass
            self.matchData.writeJsonFile()
        except Exception as e:
            module_logger.exception("message")    
            
        return msg
        
    def openURL(self,url):
        if(len(url) < 5):
            url = "http://alpha.tl/match/2392"
        try:
            webbrowser.open(url)
        except Exception as e:
            module_logger.exception("message")    

    def runSC2ApiThread(self,task):
        try:
            if(not self.SC2ApiThread.isRunning()):
                self.SC2ApiThread.startTask(task)
            else:
                self.SC2ApiThread.cancelTerminationRequest(task)

        except Exception as e:
            module_logger.exception("message")    
          
       
    def stopSC2ApiThread(self,task): 
        try:
            self.SC2ApiThread.requestTermination(task)
        except Exception as e:
            module_logger.exception("message")    
        
    def runWebsocketThread(self):
        if(not self.websocketThread.isRunning()):
            self.websocketThread.start()
        else:
            self.websocketThread.cancelKillRequest()
            
    def stopWebsocketThread(self):
        try:
            self.websocketThread.requestKill()
        except Exception as e:
            module_logger.exception("message")  
            
    def cleanUp(self):
        try:
            self.SC2ApiThread.requestTermination("ALL")
            self.webApp.terminate()
            self.saveConfig()
            self.ftpUploader.kill()
            self.websocketThread.requestKill()
            module_logger.info("cleanUp called")   
        except Exception as e:
            module_logger.exception("message")    

    def saveConfig(self):
        try:
            scctool.settings.Config.set("Form","scoreupdate",str(self.view.cb_autoUpdate.isChecked()))
            scctool.settings.Config.set("Form","togglescore",str(self.view.cb_autoToggleScore.isChecked()))
            scctool.settings.Config.set("Form","toggleprod",str(self.view.cb_autoToggleProduction.isChecked()))
            scctool.settings.Config.set("Form","playerintros", str(self.view.cb_playerIntros.isChecked()))
            scctool.settings.Config.set("FTP","upload",str(self.view.cb_autoFTP.isChecked()))
            
            cfgfile = open(scctool.settings.configFile,'w')
            scctool.settings.Config.write(cfgfile)    
            cfgfile.close()
        except Exception as e:
            module_logger.exception("message")    
        
   
    def requestScoreUpdate(self,newSC2MatchData):
        
        try:
            print("Trying to update the score")
            
            self.updateData()
            newscore = 0
            for i in range(self.matchData.getNoSets()):
                found, newscore = newSC2MatchData.compare_returnScore(self.matchData.getPlayer(0,i),\
                                                                   self.matchData.getPlayer(1,i))
                if(found and newscore != 0):
                    if(self.view.setScore(i,newscore)):
                        break
                    else:
                        continue
        except Exception as e:
            module_logger.exception("message")
            
            
    def refreshButtonStatus(self):
        
        if(not scctool.settings.twitchIsValid()):
            self.view.pb_twitchupdate.setEnabled(False)
            self.view.pb_twitchupdate.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.pb_twitchupdate.setToolTip('Specify your Twitch Settings to use this feature')   
        else:
            self.view.pb_twitchupdate.setEnabled(True)
            self.view.pb_twitchupdate.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.pb_twitchupdate.setToolTip('')  
            
        if(not scctool.settings.nightbotIsValid()):
            self.view.pb_nightbotupdate.setEnabled(False)
            self.view.pb_nightbotupdate.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.pb_nightbotupdate.setToolTip('Specify your NightBot Settings to use this feature')   
        else:
            self.view.pb_nightbotupdate.setEnabled(True)
            self.view.pb_nightbotupdate.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.pb_nightbotupdate.setToolTip('')  
            
            
        if(not scctool.settings.ftpIsValid()):
            self.view.cb_autoFTP.setEnabled(False)
            self.view.cb_autoFTP.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.cb_autoFTP.setToolTip('Specify your FTP Settings to use this feature')   
        else:
            self.view.cb_autoFTP.setEnabled(True)
            self.view.cb_autoFTP.setAttribute(Qt.WA_AlwaysShowToolTips)
            self.view.cb_autoFTP.setToolTip('')   
                    
    def requestToggleScore(self,newSC2MatchData):
        
        try:
            self.updateData()
            
            for i in range(self.matchData.getNoSets()):
                found, order = newSC2MatchData.compare_returnOrder(self.matchData.getPlayer(0,i),\
                                                                self.matchData.getPlayer(1,i))
                if(found):
                    score = self.matchData.getScore()
                    
                    if(order):
                        ToggleScore(score[0],score[1],self.matchData.getBestOf())  
                    else:
                        ToggleScore(score[1],score[0],self.matchData.getBestOf())
                    
                    return    
                    
            ToggleScore(0,0,self.matchData.getBestOf())
            
        except Exception as e:
            module_logger.exception("message")    
            
    def linkFile(self, file):
        for ext in [".png", ".jpg"]:
            if(os.path.isfile(file+ext)):
                return file+ext
        return ""
    
    def updateLogosHTML(self):
        for idx in range(2):
            filename=scctool.settings.OBShtmlDir+"/data/logo"+str(idx+1)+"-data.html"
            with open(scctool.settings.OBShtmlDir+"/data/logo-template.html", "rt") as fin:
                logo = self.linkFile(scctool.settings.OBSdataDir+"/"+"logo"+str(idx+1))
                if logo == "":
                    logo = scctool.settings.OBShtmlDir+"/src/SC2.png"
                with open(filename, "wt") as fout:
                    for line in fin:
                        line = line.replace('%LOGO%', logo)
                        fout.write(line)

             
        self.ftpUploader.cwd(scctool.settings.OBShtmlDir)   
        
        for file in ["logo1-data.html", "logo2-data.html"]:
             self.ftpUploader.upload(scctool.settings.OBShtmlDir+"/data/"+file, file)
            
        self.ftpUploader.cwd("..")
    
    def updatePlayerIntros(self, newData):
        
        module_logger.info("updatePlayerIntros")  
        self.updateData()
        
        for player_idx in range(2):
            team1 = newData.playerInList(player_idx, self.matchData.getPlayerList(0))
            team2 = newData.playerInList(player_idx, self.matchData.getPlayerList(1))
            
            if((team1 and team2) or not (team1 or team2)):
                team = ""
                logo = ""
                display = "none"
            elif(team1):
                team = self.matchData.getTeam(0)
                logo = self.linkFile(scctool.settings.OBSdataDir+"/"+"logo1")
                display = "block"
            elif(team2):
                team = self.matchData.getTeam(1)
                logo = self.linkFile(scctool.settings.OBSdataDir+"/"+"logo2")
                display = "block"
                
            if logo == "":
                logo = scctool.settings.OBShtmlDir+"/src/SC2.png"

            filename=scctool.settings.OBShtmlDir+"/intro"+str(player_idx+1)+".html"
            with open(scctool.settings.OBShtmlDir+"/data/intro-template.html", "rt") as fin:
                with open(filename, "wt") as fout:
                    for line in fin:
                        line = line.replace('%NAME%', newData.getPlayer(player_idx))
                        line = line.replace('%RACE%', newData.getPlayerRace(player_idx)+".png")
                        line = line.replace('%TEAM%', team)
                        line = line.replace('%DISPLAY%', display)
                        line = line.replace('%LOGO%', logo)
                        fout.write(line)

             
        self.ftpUploader.cwd(scctool.settings.OBShtmlDir)   
        
        for file in ["intro1.html", "intro2.html"]:
             self.ftpUploader.upload(scctool.settings.OBShtmlDir+"/"+file, file)
            
        self.ftpUploader.cwd("..")
        
    def getMapImg(self, map, fullpath = False):
        mapimg = os.path.normpath(os.path.join(scctool.settings.OBSmapDir,"src/maps", map.replace(" ","_")))
        mapimg = os.path.basename(self.linkFile(mapimg))
        if not mapimg:
            mapimg = "TBD.jpg"
            self.displayWarning("Warning: Map '{}' not found!".format(map))
            
        if(fullpath):
            return scctool.settings.OBSmapDir+"/src/maps/"+mapimg
        else:
            return  mapimg
            
    def addMap(self, file, mapname):
        _, ext = os.path.splitext(file)
        map = mapname.strip().replace(" ","_")+ext
        newfile = os.path.normpath(os.path.join(scctool.settings.OBSmapDir, "src/maps", map))
        shutil.copy(file, newfile)
        scctool.settings.maps.append(mapname)
            
    def deleteMap(self, map):
        os.remove(self.getMapImg(map,True))
        scctool.settings.maps.remove(map)
            
    def displayWarning(self, msg = "Warning: Something went wrong..."):
        self._warning = True
        self.view.statusBar().showMessage(msg)
        
    def resetWarning(self):
        warning = self._warning
        print(str(warning))
        self._warning = False
        return warning
            
    def testVersion(self):
        self.checkVersionThread.start()
        
        
    def newVersionTrigger(self,version):
        self.view.statusBar().showMessage("A new version ("+version+''') is available at https://github.com/pheenix/StarCraft-Casting-Tool''')
        
        
               