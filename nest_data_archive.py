"""
Nest Archive Parser
"""

import os, json, sys
from json import *
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from collections import OrderedDict
from ntpath import normpath, basename

class MainWindow(tk.Frame):
    
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        
        self.b = tk.Button(self, text='Select Nest Archive', command=self.extract)
        self.b.place(x=200,y=50)
        
        self.label2 = tk.Label(self, text='Extract Data')
        self.label2.place(x=200,y=100)
        
        self.Cb1 = tk.IntVar()
        self.Cb1.set(1)
        self.cb1 = tk.Checkbutton(self, text='Temperature', variable=self.Cb1)
        self.cb1.place(x=200,y=125)
        self.cb1.var = self.Cb1
        
        self.Cb2 = tk.IntVar()
        self.Cb2.set(1)
        self.cb2 = tk.Checkbutton(self, text='Rel Humidity', variable=self.Cb2)
        self.cb2.place(x=200,y=150)
        self.cb2.var = self.Cb2
        
        self.Cb3 = tk.IntVar()
        self.Cb3.set(1)
        self.cb3 = tk.Checkbutton(self, text='Dew Point', variable=self.Cb3)
        self.cb3.place(x=200,y=175)
        self.cb3.var = self.Cb3
        
        self.Cb4 = tk.IntVar()
        self.Cb4.set(0)
        self.cb4 = tk.Checkbutton(self, text='JSON', variable=self.Cb4)
        self.cb4.place(x=200,y=200)
        self.cb4.var = self.Cb4
        
    def check(self, entries, vari):
        if vari.get() == 0:
            for entry in entries:
                entry.configure(state='disabled')
        else:
            for entry in entries:
                entry.configure(state='normal')
        
    def select_dates(self, available_dates):
        t = tk.Toplevel()
        t.wm_title('Select dates to plot')
               
        dates = OrderedDict()
        
        for date in available_dates:
            year = date[0:4]
            mo = date[5:]
            
            if year not in dates.keys():
                dates[year] = OrderedDict()
        
            variable = tk.IntVar()
            variable.set(1)
            cb = tk.Checkbutton(t, text=date, variable=variable)
            cb.var = variable
            cb.grid(row=available_dates.index(date))
            dates[year][mo] = cb
            
        
        b = tk.Button(t, text='OK', command=t.destroy)
        b.grid(row=len(available_dates)+1)
        
        t.wait_window()
        return dates
    
    def extract(self):
        root.withdraw()
        cwd = normpath(os.getcwd())
        
        tempcb = self.cb1.var.get()
        humecb = self.cb2.var.get()
        dewpcb = self.cb3.var.get()
        jsoncb = self.cb4.var.get()
        
        selected_vars = OrderedDict([('(temp)', tempcb), ('(humidity)', humecb), ('(dew_point)',dewpcb)])
        
        directory = normpath(filedialog.askdirectory(initialdir=cwd,title="Select Nest Archive directory"))
        
        if not directory:
            messagebox.showerror('Nest Data Archive Viewer','No directory selected')
            
            root.destroy()
            return
        
        
        if directory.split('\\')[-1] != 'NEST_DATA':
            directory = '\\'.join(directory.split('\\')[0:directory.split('\\').index('NEST_DATA')+1])
        
        thermostat_dir = directory + "\\Nest\\thermostats"
        
        thermostat_ids = os.listdir(thermostat_dir)
        
        sensor_files = []
        json_files = []
        
        for thermostat in thermostat_ids:
            curr_dir = thermostat_dir + "/" + thermostat
            for filename in Path(curr_dir).glob('**/*.csv'):
                sensor_files.append(filename)
            for filename in Path(curr_dir).glob('**/*.json'):
                json_files.append(filename)
        
#        available_dates = []
#        
#        for filename in sensor_files:
#            available_dates.append(basename(filename)[0:7])
#            
#        selected_dates = self.select_dates(available_dates)
        
        cols = ['Date', 'Time', 'avg(temp)', 'avg(humidity)']
        
        for filename in sensor_files:
            df = pd.read_csv(filename, usecols=cols)
            try:
                all_data = all_data.append(df, ignore_index=True)
            except NameError:
                all_data = df
        
        if jsoncb != 0:
            json_data = OrderedDict()
            
            for filename in json_files:
                with open(filename) as f:
                    try:
                        json_data[filename.name.strip('.json')] = json.load(f)
                    except JSONDecodeError:
                        messagebox.showwarning('Warning', 'Unable to open JSON file %s' % filename.name)
        
        a = 6.112
        b = 17.67
        c = 243.5
                
        all_data['avg(temp)_c'] = all_data['avg(temp)']
        all_data['gamma'] = np.log(all_data['avg(humidity)']/100) + b*all_data['avg(temp)_c']/(c + all_data['avg(temp)_c'])
        all_data['avg(dew_point)'] = c*all_data['gamma']/(b-all_data['gamma'])
        all_data['avg(dew_point)'] = (all_data['avg(dew_point)']*9/5) + 32
        all_data['avg(temp)'] = (all_data['avg(temp)']*9/5) + 32
        
        all_data['date_time'] = pd.to_datetime(all_data['Date'] + ' ' + all_data['Time'])
        
        all_data['daily_avg(temp)'] = all_data.groupby(['Date'])['avg(temp)'].transform('mean')
        all_data['daily_avg(humidity)'] = all_data.groupby(['Date'])['avg(humidity)'].transform('mean')
        all_data['daily_avg(dew_point)'] = all_data.groupby(['Date'])['avg(dew_point)'].transform('mean')
        
        all_data['monthly_avg(temp)'] = all_data.groupby([all_data.Date.str[-5:-3]])['avg(temp)'].transform('mean')
        all_data['monthly_avg(humidity)'] = all_data.groupby([all_data.Date.str[-5:-3]])['avg(humidity)'].transform('mean')
        all_data['monthly_avg(dew_point)'] = all_data.groupby([all_data.Date.str[-5:-3]])['avg(dew_point)'].transform('mean')
        
        nrows = sum(i == 1 for i in selected_vars.values())
        ylabel = {'(temp)':'Temperature ($^\circ$F)', '(humidity)':'Rel Humidity (%)','(dew_point)':'Dew Point ($^\circ$F)'}
        fig, ax = plt.subplots(nrows=nrows, ncols=1, sharex=True)
        
        for key, value in selected_vars.items():
            if value == 1:
                index = list(selected_vars).index(key)
                x_data = 'date_time'
                y_all_data = 'avg' + key
                y_day_data = 'daily_avg' + key
                y_mo_data = 'monthly_avg' + key
                
                all_data.plot(x=x_data,y=y_all_data, ax=ax[index])
                all_data.plot(x=x_data,y=y_day_data,ax=ax[index])
                all_data.plot(x=x_data,y=y_mo_data,ax=ax[index], color='r')
                
                ax[index].set_ylabel(ylabel[key])
                ax[index].legend(loc='upper left')
            
        plt.xlabel('Date')
        ax[0].set_title('Average Indoor Readings')    
#        plt.show()

        json_events = {'startTs':[], 'eventType':[], 'duration':[], 'heat_target':[], 'cool_target':[]}

        for month in json_data.keys():
            for day in json_data[month].keys():
                events = json_data[month][day]['events']
                for event in events:
                    json_events['startTs'].append(pd.to_datetime(event['startTs']))
                    json_events['eventType'].append(event['eventType'])
                    json_events['duration'].append(event['duration'])
                    if ('HEAT' in event['eventType']) or ('COOL' in event['eventType']):
                        json_events['heat_target'].append(event['setPoint']['targets']['heatingTarget'])
                        json_events['cool_target'].append(event['setPoint']['targets']['coolingTarget'])
                    elif event['eventType'] == 'EVENT_TYPE_AUTOAWAY':
                        json_events['heat_target'].append(event['ecoAutoAway']['targets']['heatingTarget'])
                        json_events['cool_target'].append(event['ecoAutoAway']['targets']['coolingTarget'])
                    elif event['eventType'] == 'EVENT_TYPE_AWAY':
                        json_events['heat_target'].append(event['ecoAway']['targets']['heatingTarget'])
                        json_events['cool_target'].append(event['ecoAway']['targets']['coolingTarget'])
                    elif event['eventType'] == 'EVENT_TYPE_OFF':
                        json_events['heat_target'].append(np.nan)
                        json_events['cool_target'].append(np.nan)
                    else:
                        messagebox.showerror('Error','Uknown event type in json data %s' % event['startTs'])
                        
        json_events_df = pd.DataFrame(data=json_events)
        json_events_df['heat_target_c'] = json_events_df['heat_target']
        json_events_df['heat_target'] = (json_events_df['heat_target']*9/5) + 32
        json_events_df['duration'] = json_events_df['duration'].str.rstrip('s')
        json_events_df['duration'] = pd.to_numeric(json_events_df['duration'])
        
        fig2, ax2 = plt.subplots()
        
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Temperature Set Point($^\circ$F)')
        ln1 = json_events_df.plot(x='startTs',y='heat_target',ax=ax2, color='r')
        ax3 = ax2.twinx()
        
        ax3.set_ylabel('Time (s)')
        ln2 = json_events_df.plot(x='startTs',y='duration',ax=ax3)
        
        fig2.tight_layout()
        ax2.legend(loc='upper left')
        ax3.legend(loc='upper right')
        plt.show()
    
        root.destroy()
        return
    
def on_closing():
    paths = []
    for path in sys.path:
        if path in paths:
            sys.path.remove(path)
        else:
            paths.append(path)
            
    print('Viewer closed')
    
    root.destroy()
    return

if __name__ == "__main__":
    root = tk.Tk()
    root.title('Nest Data Archive Viewer')
    root.geometry('500x300+300+300')

    mainframe = MainWindow(root)
    mainframe.pack(fill="both", expand=True)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()