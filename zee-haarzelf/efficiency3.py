#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 20 13:49:44 2023

@author: mike
"""


import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as sp
import ROOT 
import plotly.io as pio
import plotly.express as px

pio.renderers.default='browser'

def fit_bin_size(filename):
    """Corrects for the fact that the y-bin sizes in the ROOT data are exponential.
    Returns fit parameters for a function y = a*exp(b*x) + c"""
    binsizes = np.loadtxt(filename)
    xbins = np.arange(0, len(binsizes[:, 0]))
    #fit now binsize to some sort of relation 
    popt, pcov = sp.curve_fit(exp_func, xbins, binsizes[:,1], p0 = [1, 0.1, 0])
    #plt.scatter(xbins, exp_func(xbins, *popt))
    return popt, pcov
    

def get_du_floor_rate(du, floor, hit_data):
    """Loads in data corresponding to a du and floor."""
    domstr = "DU%i" %du; floorstr = "F%i" %floor
    domattr = getattr(hit_data.Detector, domstr)
    try:
        floorattr = getattr(domattr, floorstr)
        domfloordata = floorattr.h_pmt_rate_distributions_Summaryslice
        return domfloordata
    except:
        print(domattr)
        return None 
    
def get_du_floor_data(domfloordata, pmt_per_dom):
    """Converts rootpy histogram to python-handable data."""
    domfloorhitrate = np.zeros([pmt_per_dom, 100])
    for i in range(0, pmt_per_dom):
        for j in range(0, 100):
            domfloorhitrate[i, j] = domfloordata.Integral(i, i+1, j, j+1)
            
    domfloorhitrate = domfloorhitrate.swapaxes(1, 0)
    return domfloorhitrate

def gauss(x, a, x0, sigma):
    return a*np.exp(-(x-x0)**2/(2*sigma**2))

def exp_func(x, a, b, c):
    return a*np.exp(b*x) + c

def lin_func(x, a,b):
    return a*x

def get_mean_std(mean_rate_array, axis=1):
    return np.mean(mean_rate_array, axis=axis), np.std(mean_rate_array, axis =axis)

class gaussfit():
    """Routine to get gaussian data fitted and plotted. Only requires
    the x and y data assuming it is gaussian."""
    def __init__(self, x, y):
        self.xdata = x
        self.ydata = y
        
    def gaussfunction(x, a, x0, sigma):
        return a* np.exp(-(x-x0)**2/(2*sigma**2))
        
    def mean(self):
        return np.sum(self.xdata * self.ydata) / np.sum(self.ydata)
        
    def sigma(self):
        return np.sqrt(np.sum(self.ydata * (self.xdata - self.mean())**2) / np.sum(self.ydata))
    
    def gaussfit(self):
        popt, pcov = sp.curve_fit(gauss, self.xdata, self.ydata, p0=[max(self.ydata), self.mean(), self.sigma()], maxfev = 50000)
        return popt, pcov
    
    def gaussplot(self):
        plt.plot()
        popt, pcov = self.gaussfit()
        plt.scatter(self.xdata, self.ydata, label="raw data")
        plt.plot(self.xdata, gauss(self.xdata, *popt), label="gauss fit", color="orange")
        plt.title("Gaussian of a PMT rate distribution.")
        plt.xlabel("Rate [kHz]")
        plt.legend()
        plt.show()
        return popt, pcov
    
    def get_mean_coords(self):
        popt, pcov = self.gaussfit()
        mean = self.mean()
        return mean, gauss(mean, *popt)
    
class meanhitrate():
    """Everything that has to do with the efficiency/rate arrays"""
    def __init__(self, mean_hit_rate):
        """Remember mean hit rate array has following structure:
            [runs, data, eff / pmt / du / floor / mean or something]"""
        self.meanhitrate = mean_hit_rate
        
    def avg_top_bottom_pmts(self, mid_pmt = 12):
        """Averages over the top (0-11) and bottom (12-31) pmts."""
        test = self.meanhitrate.shape
        self.meanhitrate = self.meanhitrate[~np.isnan(self.meanhitrate).any(axis=2)]
        self.meanhitrate = self.meanhitrate.reshape(test[0], int(test[1]/31), 31, 5) #block per DOM 
        self.top_avg = np.mean(self.meanhitrate[:, :, 0:mid_pmt, :], axis=2)
        self.bottom_avg = np.mean(self.meanhitrate[:, :, mid_pmt:31, :], axis=2)
        self.top_avg = self.filter_data(self.top_avg)
        #self.pmtavg = np.zeros([self.meanhitrate.shape[0]*2, self.meanhitrate.shape[2]])
        #self.pmtavg[::2, :] = self.top_avg; self.pmtavg[1::2, :] = self.bottom_avg;
        #self.top_length = self.top_avg.shape[0]
        #self.top_mask = self.top_avg[:-1] == self.top_avg[1:]
        return 0;
    
    def plot_top_bottom_pmts(self, top_avg, bottom_avg, fit=True):
        #top_avg = self.filter_data(top_avg)
        #bottom_avg = self.filter_data(bottom_avg)
        j = 0; k = 0
        if fit == True:
            uppopt, uppcov, lowpopt, lowpcov, top_mask = self.fit_top_bottom_pmts(top_avg, bottom_avg)
            xfit = np.linspace(0, 1.4, 2)
        for i in range(0, top_avg.shape[0]-1):
            if top_mask[i,2] == False: #checks if new du starts. 
                #Concatenate arrays together
                if fit == True:
                    plt.plot(xfit, lin_func(xfit, *uppopt[k,:]), label="top fit")
                    plt.plot(xfit, lin_func(xfit, *lowpopt[k, :]),label="bottom fit")
                    k = k + 1
                plt.scatter(top_avg[j:i, 0], top_avg[j:i, 4], label="average of pmts 0-11")
                plt.scatter(bottom_avg[j:i, 0], bottom_avg[j:i, 4], label="average of pmts 12-30")
                plt.scatter(np.mean(top_avg[j:i, 0]), np.mean(top_avg[j:i, 4]), label="mean point top pmts")
                plt.scatter(np.mean(bottom_avg[j:i, 0]), np.mean(bottom_avg[j:i, 4]), label="mean point bottom pmts")
                plt.title("Rate vs efficiency for du no %i" %(top_avg[i, 2]))
                plt.ylim(0, 12.5)
                plt.xlim(0, 1.4)
                plt.xlabel("Efficiency")
                plt.ylabel("Rate [kHz]")
                plt.legend()
                plt.show()
                j = i 
        return 0;


    def multi_d_plot_top_bottom_pmt(self, fit=True):
        self.top_avg = self.filter_data(self.top_avg)
        self.bottom_avg = self.filter_data(self.bottom_avg)
        #for i in range(0, self.top_avg.shape[0]):
        #    self.plot_top_bottom_pmts(self.top_avg[i, :, :], self.bottom_avg[i, :, :])
        top_mask = self.top_avg[:, :-1, :] == self.top_avg[:, 1:, :]
        k = 0; j = 0
        for i in range(0, self.top_avg.shape[1]-1):
            if top_mask[0,i,2] == False: #assume composition of du does not change over time 
                #print(np.mean(self.top_avg[:, j:i, 0], axis=1), np.mean(self.top_avg[:, j:i, 4], axis=1))
                for l in range(0, self.top_avg.shape[0]):
                    #plt.scatter(np.mean(self.top_avg[l, j:i, 0]), np.mean(self.top_avg[l, j:i, 4]), label="mean point top pmts")
                    #plt.scatter(np.mean(self.bottom_avg[l, j:i, 0]), np.mean(self.bottom_avg[l, j:i, 4]), label="mean point bottom pmts")
                    plt.scatter(3*l, np.mean(self.top_avg[l, j:i, 4]), color="orange") #top pmts
                    plt.scatter(3*l, np.mean(self.bottom_avg[l, j:i, 4]), color="blue") #bottom pmt
                j = i
                k = k + 1
                #plt.ylim(0, 12.5)
                #plt.xlim(0, 1.4)
                #plt.title("Rate vs efficiency for du no %i" %(self.top_avg[0, i, 2]))
                #plt.xlabel("Efficiency")
                #plt.ylabel("Rate [kHz]")
                plt.title("Efficiency as function of time for du no. %i" %(self.top_avg[0, i, 2]))
                plt.xlabel("hours since start")
                plt.ylabel("efficiency")
                plt.legend()
                plt.show()

        print(k) 
        return 0;
    
    def performance_per_du(self, fit=True):
        """Note top_avg 0th column refers to efficiency; 4th column to rate [khz]"""
        self.top_avg = self.filter_data(self.top_avg) #this is already averaged per pmt 
        self.bottom_avg = self.filter_data(self.bottom_avg)
        top_mask = self.top_avg[:, :-1, :] == self.top_avg[:, 1:, :] #detect change in pmt/du/string 
        j = 0; k = 0 #top du data structure [data; time; eff / pmt etc]
        top_du_data = np.zeros([len(top_mask[0,:,2]) - top_mask[0,:,2].sum(), self.top_avg.shape[0], self.top_avg.shape[2]])
        bottom_du_data = np.zeros([len(top_mask[0,:,2]) - top_mask[0,:,2].sum(), self.top_avg.shape[0], self.top_avg.shape[2]])
        print(top_du_data.shape)
        #Get mean per string 
        for i in range(0, self.top_avg.shape[1]-1): 
            if top_mask[0,i,2] == False: #assume composition of du does not change over time 
                #du_top_data = (np.mean(self.top_avg[:, j:i, :], axis = 1))
                #du_bottom_data = np.mean(self.bottom_avg[:, j:i, :], axis=1)
                top_du_data[k, :, :] = np.mean(self.top_avg[:, j:i, :], axis = 1)
                bottom_du_data[k, :, :] = np.mean(self.bottom_avg[:, j:i, :], axis=1)
                j = i+1; k = k+1
        #Organise mean per string in one array; note structure is [top/bottom; data; time dep; eff/pmt etc] i.e [2, [x], time, 5]
        total_du_data = np.zeros([2, len(top_mask[0,:,2]) - top_mask[0,:,2].sum(), self.top_avg.shape[0], self.top_avg.shape[2]])
        total_du_data[0, ...] = top_du_data
        total_du_data[1, ...] = bottom_du_data
        return total_du_data

    def performance_per_floor(self, floor_group):
        """floor_group np array or list detailling which numbers are the edges of a group.
        Note output as follows [top/bottom pmts, time, floor group, data, eff / pmt/ du / floor / mean]"""
        self.top_avg = self.filter_data(self.top_avg) #this is already averaged per pmt 
        self.bottom_avg = self.filter_data(self.bottom_avg)
        top_mask = np.isin(self.top_avg[:, :, 3], floor_group)
        #top_dom_du_data = np.zeros([])
        #print(self.top_avg.shape)
        #print(self.top_avg)
        #Average and rearrange data in [n] floor blocks; array shape time/floor group / data divided by floor groups/ headers
        top_floor_blocks_avg = np.zeros([self.top_avg.shape[0], len(floor_group), int(top_mask[0,:].sum()/len(floor_group)), self.top_avg.shape[2]])
        bottom_floor_blocks_avg = np.zeros([self.top_avg.shape[0], len(floor_group), int(top_mask[0,:].sum()/len(floor_group)), self.top_avg.shape[2]])
        j = 0; k = 0; l = 0 #top du data structure [data; time; eff / pmt etc]
        for i in range(0, self.top_avg.shape[1]):
            if top_mask[0, i] == True:
                top_floor_blocks_avg[:, k, l, :] = np.mean(self.top_avg[:, j:i+1, :], axis = 1)
                bottom_floor_blocks_avg[:, k, l, :] = np.mean(self.bottom_avg[:, j:i+1, :], axis = 1)
                j = i + 1
                if k >= 2:
                    k = 0
                    l = l + 1
                else:
                    k = k + 1
        total_du_floor_blocks_data = np.zeros([2, self.top_avg.shape[0], len(floor_group), int(top_mask[0,:].sum()/len(floor_group)), self.top_avg.shape[2]])
        total_du_floor_blocks_data[0, ...] = top_floor_blocks_avg
        total_du_floor_blocks_data[1, ...] = bottom_floor_blocks_avg
        return total_du_floor_blocks_data
        
    def time_plot_top_bottom_pmt(self):
        pmt_no = 0 #0 for top, 1 for bottom 
        eff_or_rate = 4 #0 for efficiencies, 4 for rates 
        """Try 2d heat map with x time y string number z efficiency"""
        total_du_data = self.performance_per_du()
        #Reshape array to prepare for heat map
        heatmap = np.zeros([total_du_data.shape[2], total_du_data.shape[1]])
        for i in range(0, total_du_data.shape[2]):
            heatmap[i, :] = total_du_data[pmt_no, :, i, eff_or_rate]
        heatmap = np.swapaxes(heatmap, 0, 1)
        timearr = np.linspace(0, 3*((total_du_data.shape[2])-1), num = (total_du_data.shape[2]))
        print("Initialising plot")
        fig = px.imshow(heatmap, labels=dict(x="time since start (h)", y="string number", color="rate [kHz]"), 
                        x = timearr, y=total_du_data[pmt_no, :, i, 2], text_auto=True,
                        title = "Rates of DUs as function of time for pmts 1-11")
        #fig = px.imshow(heatmap, text_auto=True, aspect="auto")
        fig.show()
        return 0;

    def string_plot_top_bottom_pmt_static(self):
        pmt_no = 1 #0 for top, 1 for bottom 
        eff_or_rate = 4 #0 for efficiencies, 4 for rates 
        if pmt_no == 0:
            pmt_no_str = "PMTs 0-11."
        else:
            pmt_no_str = "PMTs 12-30."
        """Try 2d heat map with x time y string number z efficiency"""
        total_du_data = self.performance_per_floor([6, 12, 18]) #groups floors no. 0-6; 7-12; 13-18
        #Normalise over time 
        total_du_data = np.mean(total_du_data, axis=1)
        #print(total_du_data)
        heatmap = np.zeros([total_du_data.shape[2], total_du_data.shape[1]])
        for i in range(0, total_du_data.shape[2]):
            heatmap[i, :] = total_du_data[pmt_no, :, i, eff_or_rate]
        heatmap = np.swapaxes(heatmap, 0, 1)
        print("Initialising plot")
        fig = px.imshow(heatmap, labels=dict(x="DU number",y="floor group", color="rate [kHz]"), 
                        x= total_du_data[pmt_no, 0, :, 2],y=['0-6', '7-12', '13-18'],
                        title = "Rates of DUs seperated by DOM performance per floor group, %s" %pmt_no_str, 
                        text_auto=True, aspect="auto", range_color= [2, 9])
        print(np.mean(heatmap, axis=1))
        print(np.std(heatmap, axis=1))
        if pmt_no == 0:
            fig.write_image("top-rate-string-floor-group.pdf")
        else:
            fig.write_image("bottom-rate-string-floor-group.pdf")
        return 0;

    def string_plot_top_bottom_pmt(self):
        pmt_no = 0 #0 for top, 1 for bottom 
        eff_or_rate = 4 #0 for efficiencies, 4 for rates 
        if pmt_no == 0:
            pmt_no_str = "PMTs 0-11."
        else:
            pmt_no_str = "PMTs 12-30."
        """Try 2d heat map with x time y string number z efficiency"""
        total_du_data = self.performance_per_floor([6, 12, 18]) #groups floors no. 0-6; 7-12; 13-18
        #Normalise over group
        total_du_data = np.mean(total_du_data, axis=3)
        heatmap = np.zeros([total_du_data.shape[0], total_du_data.shape[2], total_du_data.shape[1]])
        for i in range(0, total_du_data.shape[2]):
            heatmap[:, i, :] = total_du_data[:, :, i, eff_or_rate]
        #heatmap = np.swapaxes(heatmap, 0, 1) 
        heatmap = np.flip(heatmap, axis=1) #put higher number doms to the top
        print(heatmap)
        print("Initialising plot")
        timearr = np.linspace(0, 3*((total_du_data.shape[1])-1), num = (total_du_data.shape[1]))
        print(timearr)
        for i in range(0, 2):
            if i == 0:
                pmt_no_str = "PMTs 0-11."
            else:
                pmt_no_str = "PMTs 12-30."
            fig = px.imshow(heatmap[i, ...], labels=dict(x="time since start in hours",y="floor group", color="rate [kHz]"), 
                            x= timearr,y=['13-18', '7-12', '1-6'],
                            title = "Rates of DUs seperated by floor group performance, %s" %pmt_no_str, 
                            text_auto=True, aspect="auto", range_color= [4, 6], width=1980, height=1080)
            if i == 0:
                fig.write_image("top-time-rate-string-floor-group.pdf")
            else:
                fig.write_image("bottom-time-rate-string-floor-group.pdf")
        return heatmap; #heatmap structure [top/bottom pmts, floor group/time]

        
    def string_plot_top_bottom_pmt_rate_change(self, heatmap):
        print(heatmap.shape)
        heatmap_change = np.diff(heatmap, axis=2)
        print(heatmap_change.shape)
        timearr = np.arange(3, 3*(heatmap.shape[2]), 3)
        print(timearr)
        for i in range(0, 2):
            if i == 0:
                pmt_no_str = "PMTs 0-11."
            else:
                pmt_no_str = "PMTs 12-30."
            fig = px.imshow(heatmap_change[i, ...], labels=dict(x="time since start in hours",y="floor group", color="rate [kHz]"), 
                            x= timearr,y=['13-18', '7-12', '1-6'],
                            title = "Difference between rates of DUs seperated by floor group performance, %s" %pmt_no_str, 
                            text_auto=True, aspect="auto", range_color= [0, 0.02], width=1980, height=1080)
            if i == 0:
                fig.write_image("top-diff-time-rate-string-floor-group.pdf")
            else:
                fig.write_image("bottom-diff-time-rate-string-floor-group.pdf")

    def plot_top_bottom_performance(self):
        k = 0
        plt.title("Performance of various DUs")
        plt.xlabel("DU number")
        plt.ylabel("Linear fit slope")
        for i in range(0, self.top_length-1):
            if self.top_mask[i,2] == False:
                plt.plot(self.top_avg[i, 2], self.uppopt[k,0], c='red', marker="o", ls="")
                plt.plot(self.bottom_avg[i, 2], self.lowpopt[k,0], c='blue', marker="o", ls="")
                k = k + 1
        plt.scatter(np.mean(self.top_avg[:,2]), np.mean(self.uppopt[:,0]), c='darkred', marker="X", label="average performance top pmts")
        plt.scatter(np.mean(self.bottom_avg[:,2]), np.mean(self.lowpopt[:,0]), c='darkblue', marker="X", label="average performance bottom pmts")
        plt.legend()
        plt.show()
    

    def fit_top_bottom_pmts(self, top_avg, bottom_avg):
        top_mask = top_avg[:-1] == top_avg[1:]
        no_dus = top_mask.shape[0] - top_mask[:, 2].sum()
        uppopt, uppcov = np.zeros([no_dus,2]), np.zeros([no_dus, 2, 2])
        lowpopt, lowpcov = np.zeros([no_dus,2]), np.zeros([no_dus, 2, 2])
        j = 0; k = 0
        for i in range(0, self.top_avg.shape[0]-1):
            if top_mask[i,2] == False:
                uppopt[k,:], uppcov[k, :, :] = sp.curve_fit(lin_func, top_avg[j:i, 0], top_avg[j:i, 4])
                lowpopt[k,:], lowpcov[k, :, :] = sp.curve_fit(lin_func, bottom_avg[j:i, 0], bottom_avg[j:i, 4])
                j = i; k = k + 1
        return uppopt, uppcov, lowpopt, lowpcov, top_mask

    def filter_data(self, avg_arr):
        """Removes all outliers greater than say 3 sigma from the average"""
        top_mean, top_std = get_mean_std(avg_arr)
        topdiff = np.abs(np.repeat(top_mean[:, np.newaxis, :], avg_arr.shape[1], axis=1) - avg_arr)
        outliers = np.greater(np.repeat(5*top_std[:, np.newaxis, :], avg_arr.shape[1], axis=1), topdiff)
        avg_arr2 = avg_arr
        #test = (outliers[:, :, 0] * outliers[:, :, 4])
        for i in range(0, avg_arr.shape[0]): #TODO fix for-loop here 
            avg_arr2[i, :, :] = avg_arr[i, outliers[i, :, 0]]
        return avg_arr2

class extract_mean_hit_rate():

    def __init__(self, run_numbers, low_pmt, high_pmt, du_eff_map = "map.txt"):
        self.run_numbers = run_numbers
        self.du_eff_map = np.loadtxt(du_eff_map)
        self.path = "../get-data/"
        self.low_pmt, self.high_pmt = low_pmt, high_pmt

    def get_map_data(self, effs, pmt_per_dom):
        """Substitutes module-id for corresponding efficiency and generates a mapping
        of efficiencies to du and floor number"""
        self.effs_length = len(effs[:, 0])
        mapdata = np.zeros([len(effs[:, 0]), 4])
        for i in range(0, len(effs)):
            if i % pmt_per_dom == 0:
                j = 0
                for l_no, line in enumerate(self.du_eff_map): #first search for number then use that for next 31 entries.
                    if effs[i,0] in line:
                        du, floor = line[1], line[2]
                        #Note PMT-channel is 0 through 30 repetitive 
            mapdata[i, :] = [effs[i, 2],j, du, floor] # efficiency / pmt-channel/ no du/ no floor
            j = j + 1
        return mapdata

    def read_mapdata(self, str_effs):
        """Reads in data, returns a map of the efficiencies to du and floor and returns 
        a list of dus and floors """
        effs = np.loadtxt(str_effs, skiprows = 148, usecols=[1,2,3])
        pmt_per_dom = self.high_pmt - self.low_pmt
        mapdata = self.get_map_data(effs ,pmt_per_dom)
        return mapdata

    def analysis_mul_runs(self):
        for i in range(0, len(self.run_numbers)):
                str_effs = self.path + "KM3NeT_00000133_000%i.v8.0_PMTeff_new.ToT.QE.PMTeff.txt" %(self.run_numbers[i])
                mapdata = self.read_mapdata(str_effs)
                mapdata = mapdata[np.lexsort((mapdata[:, 3], mapdata[:, 2]))]
                if i == 0:
                    effs = np.loadtxt(str_effs, skiprows = 148, usecols=[1,2,3])
                    mapdata_large = np.zeros([len(self.run_numbers), len(effs[:, 0]), 4])
                    del effs
                mapdata_large[i, :, :] = mapdata #runs vs length data vs cols containing efficiency / pmt-channel / no du / no floor
        self.mapdata_large = mapdata_large
        return mapdata_large

    def read_root_data(self):
        mean_hit_rate = np.zeros([self.mapdata_large.shape[0], self.mapdata_large.shape[1], 5]) # eff / pmt / du / floor / mean or something
        #mean_hit_rate.astype(np.float32)
        mean_hit_rate[:, :, 0:4] = np.copy(self.mapdata_large)
        bin_popt, bin_pcov = fit_bin_size("y-bin_size.txt") #assume bin sizes constant over all runs
        for l in range(0, len(self.run_numbers)):
            hit_data = ROOT.TFile.Open(self.path + "jra_133_%i.root" %(self.run_numbers[l]))
            j = 0
            ytest = np.arange(0, 100)
            for i in range(0,int(self.mapdata_large.shape[1]/31)):
                dufloordata = get_du_floor_rate(int(mean_hit_rate[l, j, 2]), int(mean_hit_rate[l, j, 3]), hit_data)
                if dufloordata != None:
                    dufloorhitrate = get_du_floor_data(dufloordata, 31)
                    for k in range(0, 31):
                        test = gaussfit(ytest, dufloorhitrate[:, k]) #gets gaussian of hits per rate per pmt 
                        mean_hit_rate[l, j + k, 4] = exp_func(test.get_mean_coords()[0], *bin_popt) 
                #to convert bins to real unit as the y-bin size is log
                else:
                    mean_hit_rate[j:j+31, 4] = np.nan
                j = j + 31
        self.mean_hit_rate = mean_hit_rate
        print(mean_hit_rate.shape)
        return mean_hit_rate




def main():
    run_numbers = np.arange(14413,14440, 1)
    #run_numbers = np.arange(14413, 14416, 1)
    test = extract_mean_hit_rate(run_numbers, 0, 31)
    test.analysis_mul_runs()
    
    test2 = meanhitrate(test.read_root_data())
    test2.avg_top_bottom_pmts()
    heatmap = test2.string_plot_top_bottom_pmt()
    test2.string_plot_top_bottom_pmt_rate_change(heatmap)

if __name__ == "__main__":
    main()