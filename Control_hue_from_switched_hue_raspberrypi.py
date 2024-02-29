# -*- coding: utf-8 -*-
"""
Created on Sun Sep 16 15:35:28 2018

@author: EG-Desk

This script will monitor a 'Switched' hue lamp (one who's power will be turned on and off by a switch 
   and thus make the lamp unreachable) and then control both a 'Controlled' lamp (a "slave" to
   the Switched) and a 'Signal' lamp (that will turn on when Switched goes from unreachble to reachable but otherwise
   is unaffected - unless within special hours).
   
######################### Autorun stuff #########################

A link to this file has been put into the autorun folder:
/etc/xdg/lxsession/LXDE-pi/autostart

using the '@' will allow the pi to re-try the command if it fails

@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@lxterminal -e python3 /path/my_script.py

######################### Philips Hue instructions #########################

First install the Philips Hue library: 
sudo python3 -m pip install qhue

Info: https://pypi.org/project/qhue/
More here: https://developers.meethue.com/documentation/getting-started


Also:
sudo python3 -m pip install rich # for colors on terminal
sudo python3 -m pip install pynput # for keyboard interactivity

Find USERNAME by typing the URL "/api" and in the Body, type "{"devicetype":"my_hue_app"}"
Push the button on the hub, then click on POST.

To find info about what lamps exist, open a browser and typeL: http://192.168.1.55/debug/clip.html to get the hub.
In the interface, type in the URL: http://192.168.1.55/api/"USERNAME"/lights and then push "GET" for state info

Possible sates of a lamp (color in parenthesis):
    
"state": {
			"on": true/false,
			"bri": 0-254,
			"alert": "select",
			"mode": "homeautomation",
			"reachable": true/false,
            
            ("hue": 8120,)
			("sat": 167,)
			("effect": "none",)
			("xy": [
				0.4762,
				0.4134
			],)
			("ct": 396,)
            ("colormode": "xy",)
		}

##########################################################################
"""
from qhue import Bridge
import time
import datetime
import csv
#import msvcrt
from rich import print
#import sys
import os
# to get terminal to work with colors 
#import ctypes
# to get keypress
#import keyboard
from pynput import keyboard

# Hue hub static IP set at router
BRIDGE_IP_ADDRESS = "192.168.1.55"
#USERNAME = "Quotg6cHMlv5XSsF0jYMhmJNxi6wnnVMUKfBknWA" # Tauric hub
USERNAME = "d1nZ5y7ZzwzI97etVYsZ1lBj9EqfcX9-47KgVv3C" # "egraham.cens" on mom's hub

# Poll the hub every 'CHECK_TIME', in seconds
#   note that this polling is also controlled by the TIME_IGNORE constant (below)
CHECK_TIME = 30

# Time for events (no signal, turn off signal)
# If switched lamp gets turned on then off between these times, then turn off the signal lamp also
#   Note: this is in the evening hours but does not span midnight.  Logic is: now > START & now < END
#   any time rame spanning midnight will require an "or".  Set to 'None' to not use this function
TIME_TURNOFF_SIGNAL_START = 18
TIME_TURNOFF_SIGNAL_END = 22
#TIME_TURNOFF_SIGNAL_START = None
#TIME_TURNOFF_SIGNAL_END = None

# Time of day to care about swithing on or off = ignore events during these times
#   Note: this is in the daytime hours and so does NOT spans midnight.  Logic is: now > START & now < END
#   any other time frame will need to adjust logic below.  Set to 'None' to not use this function
TIME_IGNORE_START = 9
TIME_IGNORE_END = 18
#TIME_IGNORE_START = None
#TIME_IGNORE_END = None

# keyboard input
global keypressed
keypressed = ""

## For colors on Windows machine
# class colors:
# # Colors class:reset all colors with colors.reset; two sub classes fg for foreground
# #  and bg for background; use as colors.subclass.colorname. 
# #  i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
# #  underline, reverse, strike through,
# #  and invisible work with the main class i.e. colors.bold
# # Commented unused values for cleanliness

#     reset = '\033[0m'
#     # bold = '\033[01m'
#     # disable = '\033[02m'
#     # underline = '\033[04m'
#     # reverse = '\033[07m'
#     # strikethrough = '\033[09m'
#     # invisible = '\033[08m'
 
#     class fg:
#         # black = '\033[30m'
#         red = '\033[31m'
#         green = '\033[32m'
#         # orange = '\033[33m'
#         # blue = '\033[34m'
#         # purple = '\033[35m'
#         # cyan = '\033[36m'
#         # lightgrey = '\033[37m'
#         # darkgrey = '\033[90m'
#         # lightred = '\033[91m'
#         # lightgreen = '\033[92m'
#         yellow = '\033[33m'
#         ## reverse yellow
#         ryellow = '\033[33m\033[07m'
#         # # bold yellow
#         # byellow = '\033[33m\033[01m'
#         # lightblue = '\033[94m'
#         # pink = '\033[95m'
#         # lightcyan = '\033[96m'
     
#     # class bg:
#     #     black = '\033[40m'
#     #     red = '\033[41m'
#     #     green = '\033[42m'
#     #     orange = '\033[43m'
#     #     blue = '\033[44m'
#     #     purple = '\033[45m'
#     #     cyan = '\033[46m'
#     #     lightgrey = '\033[47m'
        
    
# # Append to file times and status of all lamps
# This has been commented out to reduce wear on the SD card
# def log_to_file(filename, lamps_status):
    # if not lamps_status == "":
        # try:
            # with open(filename, 'a', newline='') as csvfile:
                # writer = csv.writer(csvfile)
                # writer.writerow(lamps_status)
        # except IOError:
            # print("")
            # print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            # print("An [red]ERROR[/red] was encountered while logging to file!")
            # print("File %s does not exist (or other problem)!" % filename)


# Get status of lamps for decision making and display
def get_status(b, lamps):
    # Sometimes the hub returns an "unreachable" when the lamp is actually on.  
    #   So, in the event of an error or one of the lamps not being reachable, repeat twice more.
    tries = 0
    
    # First, get the status of all lamps on the hub
    lamps_status = {"SwitchedR":False, "SwitchedO":False,
                    "ControlledR":False, "ControlledO":False,
                    "SignalR":False, "SignalO":False, "Error": False}
    while tries < 3:
        try:
            # 'lampstatus' is a dictionary of all lights on the hub, not just the ones of interest
            all_lamps_status = b.lights()
            lamps_status['Error'] = False
        except:
            # set error flag on lamps_status to True
            lamps_status['Error'] = True
        
        # get lamp info for our lamps only.  R = reachable, O = on
        if not lamps_status['Error']:
            lamps_status['SwitchedR'] = all_lamps_status[str(lamps['Switched'])]['state']['reachable']
            if not lamps_status['SwitchedR']:
                # hub reports last state of lamp, on or off, even if unreachable.  Fix this here
                lamps_status['SwitchedO'] = False
            else: 
                lamps_status['SwitchedO'] = all_lamps_status[str(lamps['Switched'])]['state']['on']
            
            lamps_status['ControlledR'] = all_lamps_status[str(lamps['Controlled'])]['state']['reachable']
            if not lamps_status['ControlledR']:
                # hub reports last state of lamp, on or off, even if unreachable.  Fix this here
                lamps_status['ControlledO'] = False
            else: 
                lamps_status['ControlledO'] = all_lamps_status[str(lamps['Controlled'])]['state']['on']
            
            lamps_status['SignalR'] = all_lamps_status[str(lamps['Signal'])]['state']['reachable']
            if not lamps_status['SignalR']:
                # hub reports last state of lamp, on or off, even if unreachable.  Fix this here
                lamps_status['SignalO'] = False
            else: 
                lamps_status['SignalO'] = all_lamps_status[str(lamps['Signal'])]['state']['on']
        
        # if the switched AND the signal are unreachable, or ane error, try again
        if ((not lamps_status['SwitchedR']) & (not lamps_status['SignalR'])) | (lamps_status['Error']):
            time.sleep(2)
            tries = tries + 1
            print(tries, end="", flush=True)
        else:
            tries = 3
    
    # if we can't communicate with the hub after 3 tries
    if lamps_status['Error']:
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        print("An [red]ERROR[/red] was encountered while communicating with hub!")
        print("")
    
    return lamps_status
        

# set the status ('state', either on or off) of a lamp through the hub, 
#   will return False=on and error=True if problems
def set_status(b, lampnum, statevalue):
    if statevalue == 'on':
        try:
            b.lights[str(lampnum)].state(on=True)
            success_status = True
        except:
            print("")
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            print("An [red]ERROR[/red] was encountered while communicating with hub!")
            print("Failed to set status to 'on':", lampnum, statevalue)
            print("")
            success_status = False
    elif statevalue == 'off':
        try:
            b.lights[str(lampnum)].state(on=False)
            success_status = True
        except:
            print("")
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            print("An [red]ERROR[/red] was encountered while communicating with hub!")
            print("Failed to set status to 'off':", lampnum, statevalue)
            print("")
            success_status = False
    return success_status
       

# blink to on
def blink_to_on(b, lampnum, statevalue):
    if statevalue == 'on':
        n = 3
        for i in range(0, n): 
            set_status(b, lampnum, 'off')
            time.sleep(2)
            set_status(b, lampnum, 'on')
            time.sleep(2)
        success_status = set_status(b, lampnum, 'on')
    return success_status


# print to screen status of all three lamps
def display_status(lamps_status):
    print("")
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("'0' to exit \n'1' to toggle Switched lamp \n'2' to toggle Controlled lamp \n'3' to toggle Signal lamp \nAny other key to refresh status \n")
    if (TIME_IGNORE_START is not None) & (TIME_IGNORE_END is not None):
        if (datetime.datetime.now().hour >= TIME_IGNORE_START) & (datetime.datetime.now().hour < TIME_IGNORE_END):
            print("Currently ignoring lamps! Not actively switching until hour is:", TIME_IGNORE_END, "\n")
    #  Switched status
    if lamps_status['Error']:
        print("An [red]ERROR[/red] was encountered while communicating with hub!")
    else:
        if lamps_status['SwitchedR']:
            if lamps_status['SwitchedO']:
                print("Switched is [green]reachable[/green] and [yellow]on[/yellow]")
            else:
                print("Switched is [green]reachable[/green] and off")
        else:
            print("Switched is [red]unreachable[/red]")
        # controlled status
        if lamps_status['ControlledR']:
            if lamps_status['ControlledO']: 
                print("Controlled is [green]reachable[/green] and [yellow]on[/yellow]")
            else:
                print("Controlled is [green]reachable[/green] and off")
        else:
            print("Controlled is [red]unreachable[/red]")
        # signal status
        if lamps_status['SignalR']:
            if lamps_status['SignalO']: 
                print("Signal lamp is [green]reachable[/green] and [yellow]on[/yellow]")
            else:
                print("Signal lamp is [green]reachable[/green] and off")
        else:
            print("Signal lamp is [red]unreachable[/red]")
    print("")

# keyboard input
def on_press(key):
    global keypressed
    try:
        keypressed=key.char
    except:
        pass
    
        
def main():
    global keypressed
    # to get terminal to work with colors on windows machine:
    #kernel32 = ctypes.WinDLL('kernel32')
    #hStdOut = kernel32.GetStdHandle(-11)
    #mode = ctypes.c_ulong()
    #kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
    #mode.value |= 4; kernel32.SetConsoleMode(hStdOut, mode)
    
    # Hue hub stuff
    b = Bridge(BRIDGE_IP_ADDRESS, USERNAME)
    # lamps are: 
    lamps = {'Switched': 9, 'Controlled': 10, 'Signal': 11}
    
    # # Log file stuff
    # filename = "Control_lamps.csv"
    # lamps_header = ["Date_time", "Switched_reachable", "Switched_on", "Controlled_reachable", "Controlled_on", "Signal_reachable", "Signal_on", "Hub_error"] 
    # lamps_status = ""
    
    # # If first time writing to log file, write header
    # if not os.path.exists(filename):
        # log_to_file(filename, lamps_header)
    
    # first-pass on startup, display lamp status
    print("")
    print("Starting")
    lamps_status = get_status(b, lamps)
    display_status(lamps_status)
    # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
    # log_to_file(filename, # lamps_file_output)
    
    # keep track of transitions from switched off to on, start as if lamp was always available
    Switched_was_unreachable = False
    lamps_status_old = lamps_status.copy()
    running = True
    
    # start listening to the keyboard (is Thread)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    # While running, check for status of Switched:
    #   If Switched is off, check status of controlled.  If on, turn off.  If off, leave it alone.
    #   If Switched is on, check status of controlled.  If on, leave on, if off, turn on.
    #   If Switched is unreachable (turned off at the switch), check status of controlled.  If on, turn off.  If off, leave it alone.
    #
    # It may be that the hub does not update, or we want to do somethign else in the future, so all cases are represented
    #   in the loop (e.g., if the controlled power is off)
    
    while running:
        now = datetime.datetime.now()
        time.sleep(1)
        
        ############################ Toggle lamps with keyboard input ################################
        
        # Keypress will stop the program gracefully and/or control the lights
        if keypressed == '0':
            print("")
            print("Key pressed", now.strftime("%Y-%m-%d %H:%M"))
            print("Ending program.")
            running = False
            
        # toggle Switched lamp
        elif keypressed == '1': # toggle Switched lamp
            if lamps_status['SwitchedR']: # if it's reachable
                if lamps_status['SwitchedO']: # if it's on
                    print("Switched lamp is [yellow]on[/yellow], turning it off.")
                    set_status(b, lamps['Switched'], 'off')
                else: # it's off, turn it on
                    print("Switched lamp is off, turning it [yellow]on[/yellow].")
                    set_status(b, lamps['Switched'], 'on')
            else: # it's unreachable
                print("Switched lamp is [red]unreachable![/red]")
            lamps_status = get_status(b, lamps)
            display_status(lamps_status)
            keypressed = ""
        
        elif keypressed == '2': # toggle Controlled lamp
            if lamps_status['ControlledR']: # if it's reachable
                if lamps_status['ControlledO']: # if it's on
                    print("Controlled lamp is [yellow]on[/yellow], turning it off.")
                    set_status(b, lamps['Controlled'], 'off')
                else: # it's off, turn it on
                    print("Controlled lamp is off, turning it [yellow]on[/yellow].")
                    set_status(b, lamps['Controlled'], 'on')
            else: # it's unreachable
                print("Controlled lamp is [red]unreachable![/red]")
            lamps_status = get_status(b, lamps)
            display_status(lamps_status)
            keypressed = ""
        
        elif keypressed == '3': # toggle Signal lamp
            if lamps_status['SignalR']: # if it's reachable
                if lamps_status['SignalO']: # if it's on
                    print("Signal lamp is [yellow]on[/yellow], turning it off.")
                    set_status(b, lamps['Signal'], 'off')
                else: # it's off, turn it on
                    print("Signal lamp is off, turning it [yellow]on[/yellow].")
                    blink_to_on(b, lamps['Signal'], 'on')
                    #set_status(b, lamps['Signal'], 'on')
            else: # it's unreachable
                print("Signal lamp is [red]unreachable![/red]")
            lamps_status = get_status(b, lamps)
            display_status(lamps_status)
            keypressed = ""
        
        ######################### End keyboard input stuff #######################
        
        # if CHECK_TIME seconds
        if now.second % CHECK_TIME == 0:
            # get lamp info.
            lamps_status = get_status(b, lamps)
            # if there is an error when reaching the lamp, punt and wait until next round
            if lamps_status['Error']:
                # indicate that the program is running, but there has been an error
                print("E", end="", flush=True)
            else:        
                # make sure doesn't run twice if there are problems
                time.sleep(2)
                
                # every hour, or if the status has changed, report status of lamps to terminal
                if ((now.minute == 0) & (now.second < 10)) | (lamps_status_old != lamps_status):              
                    display_status(lamps_status)
                    lamps_status_old = lamps_status.copy()
                    
                # if we are within the time to turn on and off lamps, or if not set
                if (not (now.hour >= TIME_IGNORE_START) & (now.hour < TIME_IGNORE_END)) | ((TIME_IGNORE_START is None) & (TIME_IGNORE_END is None)):
                    ##########################################################################
                    ################### On-off Logic, below ##################################
                    ##########################################################################
                    # if Switched and Controlled lamps are both reachable
                    if (lamps_status['SwitchedR']) & (lamps_status['ControlledR']):
                        # if signal is not reachable, continue but print warning to terminal
                        if not lamps_status['SignalR']:
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("[yellow]Warning:[/yellow] Signal lamp is unreachable!")
                            print("")
                        #print("all lamps reachable")
                        
                        # If both signal and controlled are both on.
                        if (lamps_status['SwitchedO']) & (lamps_status['ControlledO']):
                            # unlikely since Controlled is on, unless controlled by app
                            if Switched_was_unreachable: 
                                print("")
                                print(now.strftime("%Y-%m-%d %H:%M"))
                                print("Switched lamp is on, turning Signal on.")
                                blink_to_on(b, lamps['Signal'], 'on')
                                #set_status(b, lamps['Signal'], 'on')
                                lamps_status = get_status(b, lamps)
                                display_status(lamps_status)
                                # Write to file
                                # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                                # log_to_file(filename, # lamps_file_output)
                                # Action took place (Signal turned on), so now normal running
                                Switched_was_unreachable = False
                            else:
                                # indicate that the program is running
                                print(".", end="", flush=True)
                        
                        # If they are both off        
                        elif (not lamps_status['SwitchedO']) & (not lamps_status['ControlledO']):
                            #print("all of")
                            if Switched_was_unreachable:
                                Switched_was_unreachable = False
                            # indicate that the program is running
                            print(".", end="", flush=True)
                        
                        # If Switched is reachable and on but Controlled is off, turn on Controlled and examine Signal
                        # this will happen when someone switches on the Switched lamp
                        elif (lamps_status['SwitchedO']) & (not lamps_status['ControlledO']):
                            # if this is the first time the Switched is reachable and on, turn on Signal
                            if Switched_was_unreachable:
                                #set_status(b, lamps['Signal'], 'on')
                                blink_to_on(b, lamps['Signal'], 'on')
                                lamps_status = get_status(b, lamps)
                                Switched_was_unreachable = False
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("Switched lamp is on, turning Controlled on.")
                            set_status(b, lamps['Controlled'], 'on')
                            lamps_status = get_status(b, lamps)
                            display_status(lamps_status)
                            # Write to file
                            # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                            # log_to_file(filename, # lamps_file_output)
                            
                        # if Switched is reachable and off but Controlled is on, turn off Controlled, do nothing to Signal
                        # Switched could have been turned off with app
                        elif (not lamps_status['SwitchedO']) & (lamps_status['ControlledO']):
                            # If Swtiched entered reachable state off, we won't signal
                            if Switched_was_unreachable:
                                Switched_was_unreachable = False
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("Switched lamp is off, turning Controlled lamp off.")
                            set_status(b, lamps['Controlled'], 'off')
                            lamps_status = get_status(b, lamps)
                            display_status(lamps_status)
                            # Write to file
                            # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                            # log_to_file(filename, # lamps_file_output)
                            
                    # if the Switched lamp has been turned off at the switch to make it unreachable, turn off Controlled
                    # this will happen when someone switches off the Switched lamp
                    elif (not lamps_status['SwitchedR']) & (lamps_status['ControlledR']):
                        Switched_was_unreachable = True
                        # if the controlled lamp is already off, do nothing
                        if not lamps_status['ControlledO']:
                            # indicate that the program is running
                            print(".", end="", flush=True)
                        # otherwise, turn off controlled lamp
                        else:
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("Switched lamp is switched off, turning Controlled lamp off.")
                            set_status(b, lamps['Controlled'], 'off')
                            # if we want to turn off the signal lamp also
                            if (TIME_TURNOFF_SIGNAL_START is not None) & (TIME_TURNOFF_SIGNAL_END is not None):
                                if (now.hour > TIME_TURNOFF_SIGNAL_START) & (now.hour < TIME_TURNOFF_SIGNAL_END):
                                    print("Within Signal lamp off-time, turning Signal lamp off.")
                                    set_status(b, lamps['Signal'], 'off')
                            lamps_status = get_status(b, lamps)
                            display_status(lamps_status)
                            # Write to file
                            # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                            # log_to_file(filename, # lamps_file_output)
                            
                    # if both the lamps have been turned off at the switch to make them both unreachable
                    # this should be uncommon, as the controlled should always have power
                    # Possible error!
                    elif (not lamps_status['SwitchedR']) & (not lamps_status['ControlledR']):
                        Switched_was_unreachable = True
                        # if signal is also unreachable, continue but print warning to terminal
                        if not lamps_status['SignalR']:
                            print("")
                            print("[yellow]Warning:[/yellow] ALL lamps are unreachable!")
                            print("")
                        # only Switched and controlled are unreachable
                        else:
                            print("")
                            print("[yellow]Warning:[/yellow] Switched and Controlled lamps are unreachable!")
                            print("")
                    
                    # if only the controlled lamp has been turned off at the switch to make it unreachable
                    # this should be uncommon, as the controlled should always have power
                    elif (lamps_status['SwitchedR']) & (not lamps_status['ControlledR']):
                        # if Switched is on
                        if (lamps_status['SwitchedO']):
                            # if this is the first time the Switched is reachable and on, turn on Signal
                            if Switched_was_unreachable:
                                # turn on the Signal
                                #set_status(b, lamps['Signal'], 'on')
                                blink_to_on(b, lamps['Signal'], 'on')
                                lamps_status = get_status(b, lamps)
                                Switched_was_unreachable = False
                                
                                # since we don't know the status of the Controlled, log as if Controlled had been off
                                print("")
                                print(now.strftime("%Y-%m-%d %H:%M"))
                                print("Switched lamp is on.")
                                # if signal is also not reachable, continue but print warning to terminal
                                if not lamps_status['SignalR']:
                                    print("")
                                    print("[yellow]Warning:[/yellow] Signal and Controlled lamps are unreachable!")
                                    print("")
                                # only Controlled is unreachable
                                else:
                                    print("")
                                    print("[yellow]Warning:[/yellow] Controlled lamp is unreachable!")
                                    print("")
                                
                                #set_status(b, lamps['Controlled'], 'on')
                                display_status(lamps_status)
                                # Write to file
                                # lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                                # log_to_file(filename, # lamps_file_output)
                            # Switched has been on, print info about Controlled
                            else:
                                print("")
                                print("[yellow]Warning:[/yellow] Controlled lamp is unreachable!")
                                print("")
                        # if Switched is off, do nothing but print warning about the Controlled
                        else:
                            print("")
                            print("[yellow]Warning:[/yellow] Controlled lamp is unreachable!")
                            print("")
    listener.stop()

if __name__ == "__main__":
    main()
