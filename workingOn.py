import os
import re
import json
import mainwindow
from tfs import TFSAPI
from datetime import datetime
from PyQt5 import QtWidgets
from PyQt5.QtGui import QPixmap, QIcon

class WorkingOnWindow(QtWidgets.QMainWindow, mainwindow.Ui_Form):

    tray = None

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.btStart.pressed.connect(self.start_task)
        self.btStop.pressed.connect(self.stop_task)
        self.btRefresh.pressed.connect(self.refresh_query)
        self.btSave.pressed.connect(self.save_setting)
        self.btStart.setEnabled(start_flag)
        self.btStop.setEnabled(stop_flag)
        pixmap = QPixmap("custom_icons/stopwatch.ico")

        # Initialization QSystemTrayIcon
        self.tray = QtWidgets.QSystemTrayIcon()
        self.tray.setIcon(QIcon(pixmap))

        # Tray menu
        self.actionStart.triggered.connect(self.start_task)
        self.actionStop.triggered.connect(self.stop_task)
        self.actionExit.triggered.connect(QtWidgets.qApp.quit)
        tray_menu = QtWidgets.QMenu()
        tray_menu.addAction(self.actionStart)
        tray_menu.addAction(self.actionStop)
        tray_menu.addAction(self.actionExit)
        self.tray.setContextMenu(tray_menu)
        self.actionStart.setEnabled(start_flag)
        self.actionStop.setEnabled(stop_flag)
        self.tray.activated.connect(self.onTrayIconActivated)
        self.tray.show()

    def start_task(self):
        """Starts task and save last state and time to data_file"""
        with open(configs['data_file'], "w") as fw:
            json.dump({"taskID": self.cmbWorkItems.currentData(),"time": str(datetime.now())[:-7], "flag": 1}, fw)
            self.btStart.setEnabled(False)
            self.btStop.setEnabled(True)
            self.actionStart.setEnabled(False)
            self.actionStop.setEnabled(True)
        window.update()

    def stop_task(self):
        """Stops task and save last state and time to data_file and push update to the TFS server"""
        output_time = json.load(open(configs['data_file']))
        work_item_id = self.cmbWorkItems.currentData()
        work_item = client.get_workitem(work_item_id)
        work_time = {"taskID": work_item_id, "time": str(datetime.now())[:-7], "flag": 0}
        with open(configs['data_file'], "w") as fp:
            diff = datetime.now() - datetime.strptime(output_time['time'], configs['time_format'])
            json.dump(work_time, fp)
            self.btStart.setEnabled(True)
            self.btStop.setEnabled(False)
            self.actionStart.setEnabled(True)
            self.actionStop.setEnabled(False)
            if work_item["Microsoft.VSTS.Scheduling.CompletedWork"] is None:
                work_item["Microsoft.VSTS.Scheduling.CompletedWork"] = 0
            # adding time
            work_item["Microsoft.VSTS.Scheduling.CompletedWork"] = work_item["Microsoft.VSTS.Scheduling.CompletedWork"] + round(diff.total_seconds() / 3600, 2)
        print(work_item["Microsoft.VSTS.Scheduling.CompletedWork"])
        window.update()

    def refresh_query(self):
        """Refreshes combobox with tasks"""
        self.cmbWorkItems.clear()
        query = client.run_query(configs['query'])
        work_items = query.workitems
        for item in work_items:
            self.cmbWorkItems.addItem((str(item['ID']) + ": " + item['Title']), item['ID'])
        self.choose_element()

    def choose_element(self):
        """Chooses saved element from 'data_file'"""
        output_time = json.load(open(configs['data_file']))
        index = self.cmbWorkItems.findData(output_time['taskID'])
        if index >= 0:
            self.cmbWorkItems.setCurrentIndex(index)

    def init_setting(self):
        """First initialization Setings tab"""
        self.lToken.setText(config_token)
        self.lQuery.setText(config_query)
    
    def save_setting(self):
        """Saves settings to config.json file."""
        token = self.lToken.text()
        queries = self.lQuery.text()
        if validate_setting(token, queries):
            with open("config.json","r") as config_file:
                configs = json.load(config_file)
            configs['token'] = token
            configs['query'] = queries
            if validate_setting(token, queries):
                with open("config.json","w") as config_file:
                    json.dump(configs, config_file)
                
    def onTrayIconActivated(self, reason):
        """Returns minimized window to original state"""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.showNormal()

def create_template_config_file():
    """Creates default template"""
    configs = { "server": "https://<yourcompany>.visualstudio.com/", 
                "project": "<yourcompany>", 
                "data_file": "time.json", 
                "time_format": "%Y-%m-%d %H:%M:%S", 
                "token": "<place_your_token_here>", 
                "query": "<place_your_query_here>" }
    with (open('config.json',"w")) as config_file:
        json.dump(configs, config_file)

def validation():
    """Validates config files and saved token and query, create data_file if necessary"""
    try:
        with open('config.json') as config_file:
            try:
                configs = json.load(config_file)
            except:
                file_size = os.stat('config.json').st_size
                if file_size == 0:
                    create_template_config_file()
                return False
    except:
        create_template_config_file()
        return False

    if not validate_setting(configs['token'],configs['query']):
        return False

    try:
        json.load(open(configs['data_file']))
    except:
        time = {"taskID": 0, "time": "2020-01-01 00:00:00", "flag": 0}
        with (open(configs['data_file'],"w")) as time_file:
            json.dump(time, time_file)

    return True


def validate_setting(token, query):
    """Validates token and query"""    
    
    if len(token) < 52:
        return False

    if not re.compile("^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}").match(query):
        return False
    
    with open('config.json') as config_file:
        configs = json.load(config_file)
    client = TFSAPI(configs['server'], project=configs['project'], pat=token)
    try:
        client.run_query(query)
    except:
        error_dialog.showMessage('Check your token or query.')
        return False 

    return True


if __name__ == '__main__':
    start_flag = False
    stop_flag = False
    config_token = ''
    config_query = ''
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    window = WorkingOnWindow()
    window.show()
    error_dialog = QtWidgets.QErrorMessage()
    if validation():
        with open('config.json') as config_file:
            configs = json.load(config_file)
            config_token = configs['token']
            config_query = configs['query']
            client = TFSAPI(configs['server'], project=configs['project'], pat=config_token)
            flag = json.load(open(configs['data_file']))['flag'] == 1
            start_flag = not bool(flag)
            stop_flag = bool(flag)
            window.btStart.setEnabled(start_flag)
            window.btStop.setEnabled(stop_flag)
            window.init_setting()
            window.refresh_query()
    app.exec_()
