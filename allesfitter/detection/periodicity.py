#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 11:15:29 2020

@author:
Maximilian N. Günther
MIT Kavli Institute for Astrophysics and Space Research, 
Massachusetts Institute of Technology,
77 Massachusetts Avenue,
Cambridge, MA 02109, 
USA
Email: maxgue@mit.edu
Web: www.mnguenther.com
"""

from __future__ import print_function, division, absolute_import

#::: modules
import os, sys
import numpy as np
import matplotlib.pyplot as plt
import warnings
from astropy.stats import sigma_clip
from astropy.timeseries import LombScargle
from wotan import flatten, slide_clip

#::: my modules
from ..exoworlds_rdx.lightcurves.lightcurve_tools import plot_phase_folded_lightcurve                                                                                   
                                                                                      
#::: plotting settings
import seaborn as sns
sns.set(context='paper', style='ticks', palette='deep', font='sans-serif', font_scale=1.5, color_codes=True)
sns.set_style({"xtick.direction": "in","ytick.direction": "in"})
sns.set_context(rc={'lines.markeredgewidth': 1})




###############################################################################
#::: run a periodogram via astropy to get the dominant period and FAP
###############################################################################
def estimate_period(time, flux, flux_err, periodogram_kwargs=None, astropy_kwargs=None, wotan_kwargs=None, options=None):
    
    #==========================================================================
    #::: handle inputs
    #==========================================================================
    cadence = np.nanmedian(np.diff(time))
        
    if periodogram_kwargs is None: periodogram_kwargs = {}
    if 'minperiod' not in periodogram_kwargs: periodogram_kwargs['minperiod'] = 10. * cadence
    if 'maxperiod' not in periodogram_kwargs: periodogram_kwargs['maxperiod'] = time[-1]-time[0]
    
    if astropy_kwargs is None: astropy_kwargs = {}
    if 'sigma' not in astropy_kwargs: astropy_kwargs['sigma'] = 5
    
    if wotan_kwargs is None: wotan_kwargs = {}
    if 'slide_clip' not in wotan_kwargs: wotan_kwargs['slide_clip'] = {}
    if 'window_length' not in wotan_kwargs['slide_clip']: wotan_kwargs['slide_clip']['window_length'] = 1.
    if 'low' not in wotan_kwargs['slide_clip']: wotan_kwargs['slide_clip']['low'] = 5
    if 'high' not in wotan_kwargs['slide_clip']: wotan_kwargs['slide_clip']['high'] = 5

    if options is None: options = {}
    if 'show_plot' not in options: options['show_plot'] = False
    if 'save_plot' not in options: options['save_plot'] = False
    if 'fname_plot' not in options: options['fname_plot'] = 'periodogram'
    if 'outdir' not in options: options['outdir'] = '.'
    
    minfreq = 1./periodogram_kwargs['maxperiod']
    maxfreq = 1./periodogram_kwargs['minperiod']
    
    
    #==========================================================================
    #::: first, a global 5 sigma clip
    #==========================================================================
    ff = sigma_clip(flux, sigma=astropy_kwargs['sigma'])
    # ff /= np.ma.median(ff)
    
    
    #==========================================================================
    #::: slide clip (1 day, 5 sigma)
    #==========================================================================
    try:
        ff = slide_clip(time, ff, **wotan_kwargs['slide_clip'])
        # ff /= np.nanmedian(ff)
    except:
        print('Wotan failed and was skipped.')
        
    
    #==========================================================================
    #::: now do the periodogram
    #==========================================================================
    ind_notnan = np.where(~np.isnan(ff))
    ls = LombScargle(time[ind_notnan], ff[ind_notnan])  #Analyze our dates and s-index data using the AstroPy Lomb Scargle module
    frequency, power = ls.autopower(minimum_frequency=minfreq, maximum_frequency=maxfreq)  #Determine the LS periodogram
    best_power = np.nanmax(power)
    best_frequency = frequency[np.argmax(power)]
    FAP=ls.false_alarm_probability(best_power)                  #Calculate the FAP for the highest peak in the power array
    
    
    #==========================================================================
    #::: plots
    #==========================================================================
    if options['show_plot'] or options['save_plot']: 
        
        peak_loc=round(float(1./best_frequency),2) 
        FAP_probabilities = [0.5, 0.1, 0.01]                         #Enter FAP values you want to determine
        FAP_levels=ls.false_alarm_level(FAP_probabilities)           #Get corresponding LS Power values
        
        fig, axes = plt.subplots(5,1,figsize=[10,15], tight_layout=True)  
        axes = np.atleast_1d(axes)
        
        ax = axes[0]       
        ax.plot(time, flux, 'r.', rasterized=True)
        ax.plot(time, ff, 'b.', rasterized=True)
        ax.set(xlabel='Time (BJD)', ylabel='Flux')
        
        ax = axes[1]       
        ax.plot(time, ff, 'b.', rasterized=True)
        ax.set(xlabel='Time (BJD)', ylabel='Flux (clipped)')
        
        ax = axes[2]        
        ax.semilogx(1./frequency,power,color='b')  
        ax.plot(peak_loc, best_power, marker='d', markersize=12, color='r')                
        ax.text(peak_loc*1.2,best_power*0.95,'Peak Period: '+str(peak_loc)+' days')
        ax.text(peak_loc*1.2,best_power*0.85,'FAP: '+str(FAP))    
        ax.hlines(FAP_levels, periodogram_kwargs['minperiod'], periodogram_kwargs['maxperiod'], color='grey', lw=1)    
        ax.text(periodogram_kwargs['maxperiod'], FAP_levels[0],'0.5% FAP ', ha='right')     
        ax.text(periodogram_kwargs['maxperiod'], FAP_levels[1],'0.1% FAP ', ha='right')
        ax.text(periodogram_kwargs['maxperiod'], FAP_levels[2],'0.01% FAP ', ha='right')
        ax.set(xlabel='Period (days)', ylabel='L-S power')   
        ax.tick_params(axis='both',which='major')    
#        ax.text(peak_loc*1.2,best_power*0.75,'std_old:'+str(std_old*1e3)[0:4]+' --> '+'std_new:'+str(std_new*1e3)[0:4])    
        
        ax = axes[3]
        plot_phase_folded_lightcurve(time, ff, period=1./best_frequency, epoch=0, ax=ax)
        ax.set(ylim=[np.nanmin(ff), np.nanmax(ff)], ylabel='Flux (clipped)', xticklabels=[])
        
        ax = axes[4]
        plot_phase_folded_lightcurve(time, ff, period=1./best_frequency, epoch=0, ax=ax)
        ax.set(ylabel='Flux (clipped; y-zoom)')
        
        if options['save_plot']:
            if not os.path.exists(options['outdir']): os.makedirs(options['outdir'])
            fig.savefig(os.path.join(options['outdir'],options['fname_plot']+'.pdf'), bbox_inches='tight')
        if options['show_plot']:
            plt.show(fig)
        else:
            plt.close(fig)
            
            
    return 1./best_frequency, FAP  



###############################################################################
#::: estimate a good window length for spline knots, running median etc.
###############################################################################
# def estimate_window_length(time, flux, flux_err, periodogram_kwargs=None, wotan_kwargs=None, options=None):
#     window_length_min = 12./24. #at least 12h to not destroy planets
#     window_length_max = 1. #at most 1 day
#     cadence = np.median(np.diff(time))
#     best_period, FAP = estimate_period(time, flux, flux_err)
    
#     if best_period < 100.*cadence: 
#         window_length = best_period/10.
#     return np.min()
    
#         return best_period/10.
#     else:
#         return None
#         warnings.warn('Returning None. Best period was found to be', best_period*24*60, 'min., but cadence is only', cadence*24*60, 'min.')
        
        

###############################################################################
#::: remove periodic trends
###############################################################################
# def estimate_trend(time, flux, flux_err):
    
#     iterations = 3 
#     wotan_kwargs = {'slide_clip':{}, 'flatten':{}}
#     wotan_kwargs['slide_clip']['window_length'] = 1.
#     wotan_kwargs['slide_clip']['low'] = 3.
#     wotan_kwargs['slide_clip']['high'] = 3.
#     wotan_kwargs['flatten']['method'] = 'rspline'
#     wotan_kwargs['flatten']['window_length'] = None
#     wotan_kwargs['flatten']['break_tolerance'] = 0.5
    
#     trend = np.ones_like(time)
    
#     #::: global sigma clipping
#     flux = sigma_clip(flux, sigma_upper=3, sigma_lower=20)
    
#     #::: 1 day slide clip
#     flux = slide_clip(time, flux, **wotan_kwargs['slide_clip'])
    
#     for i in range(iterations):
#         wotan_kwargs['flatten']['window_length'] = estimate_window_length(time, flux, flux_err)
#         print(wotan_kwargs['flatten']['window_length']*10)
#         if wotan_kwargs['flatten']['window_length'] is not None:
#             flux, trend1 = flatten(time, flux, return_trend=True, **wotan_kwargs['flatten'])
#             trend += (trend1 - 1.)
#         plt.figure()
#         plt.plot(time, flux)
#         plt.title(i)
        
         
#     return trend
    
    
    