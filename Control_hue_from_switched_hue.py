# -*- coding: utf-8 -*-
"""
Created on Sun Sep 16 15:35:28 2018

@author: EG-Desk

This script will monitor a 'Switched' hue lamp (one who's power will be turned on and off by a switch 
   and thus make the lamp unreachable if no power) and then control both a 'Controlled' lamp (a "slave" to
   the Switched) and a 'Signal' lamp (will turn on when Switched goes from unreachble to reachable but otherwise
   is unaffected).

######################### Philips Hue instructions #########################

First install the support: https://pypi.org/project/qhue/
Info here: https://developers.meethue.com/documentation/getting-started

Find username by typing the URL "/api" and in the Body, type "{"devicetype":"my_hue_app"}"
Push the button on the hub, then click on POST.

To find info about what lamps exist, open a browser and typeL: http://192.168.1.55/debug/clip.html to get the hub.
In the interface, type in the URL: http://192.168.1.55/api/"username"/lights and then push "GET" for state info

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

####################### End Philips Hue instructions #######################
"""
from qhue import Bridge
import time
import datetime
import csv
import msvcrt
import sys
import os
# to get terminal to work with colors 
import ctypes

class colors:
# Colors class:reset all colors with colors.reset; two sub classes fg for foreground
#  and bg for background; use as colors.subclass.colorname. 
#  i.e. colors.fg.red or colors.bg.greenalso, the generic bold, disable,
#  underline, reverse, strike through,
#  and invisible work with the main class i.e. colors.bold
# Commented unused values for cleanliness

    reset = '\033[0m'
    # bold = '\033[01m'
    # disable = '\033[02m'
    # underline = '\033[04m'
    # reverse = '\033[07m'
    # strikethrough = '\033[09m'
    # invisible = '\033[08m'
 
    class fg:
        # black = '\033[30m'
        red = '\033[31m'
        green = '\033[32m'
        # orange = '\033[33m'
        # blue = '\033[34m'
        # purple = '\033[35m'
        # cyan = '\033[36m'
        # lightgrey = '\033[37m'
        # darkgrey = '\033[90m'
        # lightred = '\033[91m'
        # lightgreen = '\033[92m'
        yellow = '\033[33m'
        ## reverse yellow
        ryellow = '\033[33m\033[07m'
        # # bold yellow
        # byellow = '\033[33m\033[01m'
        # lightblue = '\033[94m'
        # pink = '\033[95m'
        # lightcyan = '\033[96m'
     
    # class bg:
    #     black = '\033[40m'
    #     red = '\033[41m'
    #     green = '\033[42m'
    #     orange = '\033[43m'
    #     blue = '\033[44m'
    #     purple = '\033[45m'
    #     cyan = '\033[46m'
    #     lightgrey = '\033[47m'
        
    
# Append to file times and status of all lamps
def log_to_file(filename, lamps_status):
    if not lamps_status == "":
        try:
            with open(filename, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(lamps_status)
        except IOError:
            print("")
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            print(f"{colors.reset}An {colors.fg.red}ERROR{colors.reset} was encountered while logging to file!")
            print("File %s does not exist (or other problem)!" % filename)


# Get status of lamps for decision making and display
def get_status(b, lamps):
    # First, get the status of all lamps on the hub
    lamps_status = {"SwitchedR":False, "SwitchedO":False,
                    "ControlledR":False, "ControlledO":False,
                    "SignalR":False, "SignalO":False, "Error": False}
    try:
        # 'lampstatus' is a dictionary of all lights on the hub, not just the ones of interest
        all_lamps_status = b.lights()
    except:
        print("")
        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        print(f"{colors.reset}An {colors.fg.red}ERROR{colors.reset} was encountered while communicating with hub!")
        print("")
        # set error flag on lamps_status to True
        lamps_status['Error'] = True
    
    # if we can't communicate with the hub
    if lamps_status['Error']:
        pass # error message already written to terminal, above
    
    # get lamp info for our lamps only.  R = reachable, O = on
    else:
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
            print(f"{colors.reset}An {colors.fg.red}ERROR{colors.reset} was encountered while communicating with hub!")
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
            print(f"{colors.reset}An {colors.fg.red}ERROR{colors.reset} was encountered while communicating with hub!")
            print("Failed to set status to 'off':", lampnum, statevalue)
            print("")
            success_status = False
    return success_status
       
 
# print to screen status of all three lamps
def display_status(lamps_status):
    print("")
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("Press '0' to exit, '1' to toggle Switched lamp, '2' to toggle Controlled lamp, '3' to toggle Signal lamp.")
    #  Switched status
    if lamps_status['Error']:
        print(f"{colors.reset}An {colors.fg.red}ERROR{colors.reset} was encountered while communicating with hub!")
    else:
        if lamps_status['SwitchedR']:
            if lamps_status['SwitchedO']:
                print(f"{colors.reset}Switched is {colors.fg.green}reachable{colors.reset} and {colors.fg.ryellow}on{colors.reset}.")
            else:
                print(f"{colors.reset}Switched is {colors.fg.green}reachable{colors.reset} and off.")
        else:
            print(f"{colors.reset}Switched is {colors.fg.red}unreachable{colors.reset}.")
        # controlled status
        if lamps_status['ControlledR']:
            if lamps_status['ControlledO']: 
                print(f"{colors.reset}Controlled is {colors.fg.green}reachable{colors.reset} and {colors.fg.ryellow}on{colors.reset}.")
            else:
                print(f"{colors.reset}Controlled is {colors.fg.green}reachable{colors.reset} and off.")
        else:
            print(f"{colors.reset}Controlled is {colors.fg.red}unreachable{colors.reset}.")
        # signal status
        if lamps_status['SignalR']:
            if lamps_status['SignalO']: 
                print(f"{colors.reset}Signal lamp is {colors.fg.green}reachable{colors.reset} and {colors.fg.ryellow}on{colors.reset}.")
            else:
                print(f"{colors.reset}Signal lamp is {colors.fg.green}reachable{colors.reset} and off.")
        else:
            print(f"{colors.reset}Signal lamp is {colors.fg.red}unreachable{colors.reset}.")
    print("")
       
        
def main():
    # to get terminal to work with colors:
    kernel32 = ctypes.WinDLL('kernel32')
    hStdOut = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode))
    mode.value |= 4; kernel32.SetConsoleMode(hStdOut, mode)
    
    # Hue hub stuff
    # static IP set at router
    bridge_ip_address = "192.168.1.55"
    #username = "Quotg6c...BknWA" # Tauric hub
    username = "d1nZ5y7Z...-47KgVv3C" # "egraham.cens" on mom's hub
    b = Bridge(bridge_ip_address, username)
    # lamps are: 
    lamps = {'Switched': 9, 'Controlled': 10, 'Signal': 11}
    
    # Log file stuff
    filename = "Controlled_lamps.csv"
    lamps_header = ["Date_time", "Switched_reachable", "Switched_on", "Controlled_reachable", "Controlled_on", "Signal_reachable", "Signal_on", "Hub_error"] 
    lamps_status = ""
    
    # If first time writing to log file, write header
    if not os.path.exists(filename):
        log_to_file(filename, lamps_header)
    
    # Poll the hub every 'check_time' seconds
    check_time = 30
    # keep track of transitions from switched off to on, start as if lamp were just switched on
    Switched_was_unreachable = True
    running = True
    
    print("")
    print("Starting")
    lamps_status = get_status(b, lamps)
    display_status(lamps_status)
    lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
    log_to_file(filename, lamps_file_output)
    
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
        
        # Keypress will stop the program gracefully and/or control the lights
        try:  # used try so that if user pressed other than the given key error will not be shown
            if msvcrt.kbhit(): # if a key press is waiting, read the char
                char = msvcrt.getch().decode('ASCII')
                print("")
                print("Key pressed", now.strftime("%Y-%m-%d %H:%M"))
                if char == '0': 
                    print("Ending program.")
                    try: 
                        sys.exit(130) 
                    except SystemExit: 
                        os._exit(130)
                
                # toggle lamps
                # toggle Switched lamp
                elif char == '1': 
                    if lamps_status['SwitchedR']: # if it's reachable
                        if lamps_status['SwitchedO']: # if it's on
                            print(f"Switched lamp is {colors.fg.ryellow}on{colors.reset}, turning it off.")
                            set_status(b, lamps['Switched'], 'off')
                        else: # it's off, turn it on
                            print(f"Switched lamp is off, turning it {colors.fg.ryellow}on{colors.reset}.")
                            set_status(b, lamps['Switched'], 'on')
                    else: # it's unreachable
                        print(f"Switched lamp is {colors.fg.red}unreachable{colors.reset}!")
                
                elif char == '2': # toggle Controlled lamp
                    if lamps_status['ControlledR']: # if it's reachable
                        if lamps_status['ControlledO']: # if it's on
                            print(f"Controlled lamp is {colors.fg.ryellow}on{colors.reset}, turning it off.")
                            set_status(b, lamps['Controlled'], 'off')
                        else: # it's off, turn it on
                            print(f"Controlled lamp is off, turning it {colors.fg.ryellow}on{colors.reset}.")
                            set_status(b, lamps['Controlled'], 'on')
                    else: # it's unreachable
                        print(f"Controlled lamp is {colors.fg.red}unreachable{colors.reset}!")
                
                elif char == '3': # toggle Signal lamp
                    if lamps_status['SignalR']: # if it's reachable
                        if lamps_status['SignalO']: # if it's on
                            print(f"Signal lamp is {colors.fg.ryellow}on{colors.reset}, turning it off.")
                            set_status(b, lamps['Signal'], 'off')
                        else: # it's off, turn it on
                            print(f"Signal lamp is off, turning it {colors.fg.ryellow}on{colors.reset}.")
                            set_status(b, lamps['Signal'], 'on')
                    else: # it's unreachable
                        print(f"Signal lamp is {colors.fg.red}unreachable{colors.reset}!")
                        
                lamps_status = get_status(b, lamps)
                display_status(lamps_status)
                    
        except:
            pass  # if user pressed a key other than the given key
        
        # if check_time seconds
        if now.second % check_time == 0:
            print(".", end="", flush=True)
            
            # get lamp info.
            lamps_status = get_status(b, lamps)
            # if there is an error when reaching the lamp, don't proceed
            if lamps_status['Error']:
                pass # do nothing here
            else:        
                # make sure doesn't run twice
                time.sleep(2)
                
                # every hour, report on status of lamps to terminal
                if (now.minute == 0) & (now.second < 10):              
                    display_status(lamps_status)
                
                # if Switched and Controlled lamps are reachable
                if (lamps_status['SwitchedR']) & (lamps_status['ControlledR']):
                    # if signal is not reachable, continue but print warning to terminal
                    if not lamps_status['SignalR']:
                        print("")
                        print(now.strftime("%Y-%m-%d %H:%M"))
                        print(f"{colors.fg.ryellow}Warning:{colors.reset} Signal lamp is unreachable!")
                        print("")
                    #print("all lamps reachable")
                    
                    # If they are both on.
                    if (lamps_status['SwitchedO']) & (lamps_status['ControlledO']):
                        # unlikely since Controlled is on, unless controlled by app
                        if Switched_was_unreachable: 
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("Switched lamp is on, turning Signal on.")
                            set_status(b, lamps['Signal'], 'on')
                            lamps_status = get_status(b, lamps)
                            display_status(lamps_status)
                            # Write to file
                            lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                            log_to_file(filename, lamps_file_output)
                            # Action took place (Signal turned on), so now normal running
                            Switched_was_unreachable = False
                        else:
                            pass
                    
                    # If they are both off        
                    elif (not lamps_status['SwitchedO']) & (not lamps_status['ControlledO']):
                        #print("all off")
                        if Switched_was_unreachable:
                            Switched_was_unreachable = False
                    
                    # If Switched is reachable and on but Controlled is off, turn on Controlled
                    # this will happen when mom wakes up and switches on the Switched lamp
                    elif (lamps_status['SwitchedO']) & (not lamps_status['ControlledO']):
                        # if this is the first time the Switched is reachable and on, turn on Signal
                        if Switched_was_unreachable:
                            set_status(b, lamps['Signal'], 'on')
                            lamps_status = get_status(b, lamps)
                            Switched_was_unreachable = False
                        print("")
                        print(now.strftime("%Y-%m-%d %H:%M"))
                        print("Switched lamp is on, turning controlled on.")
                        set_status(b, lamps['Controlled'], 'on')
                        lamps_status = get_status(b, lamps)
                        display_status(lamps_status)
                        # Write to file
                        lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                        log_to_file(filename, lamps_file_output)
                        
                    # if Switched is reachable and off but Controlled is on, turn off Controlled
                    # Switched could have been turned off with app
                    elif (not lamps_status['SwitchedO']) & (lamps_status['ControlledO']):
                        # If Swtiched entered reachable state off, we won't signal
                        if Switched_was_unreachable:
                            Switched_was_unreachable = False
                        print("")
                        print(now.strftime("%Y-%m-%d %H:%M"))
                        print("Switched lamp is off, turning controlled lamp off.")
                        set_status(b, lamps['Controlled'], 'off')
                        lamps_status = get_status(b, lamps)
                        display_status(lamps_status)
                        # Write to file
                        lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                        log_to_file(filename, lamps_file_output)
                        
                # if the Switched lamp has been turned off at the switch to make it unreachable, turn off controlled
                # this will happen when mom goes to bed and switches off the Switched lamp
                elif (not lamps_status['SwitchedR']) & (lamps_status['ControlledR']):
                    Switched_was_unreachable = True
                    # if the controlled lamp is already off, do nothing
                    if not lamps_status['ControlledO']:
                        pass
                    # otherwise, turn off controlled lamp
                    else:
                        print("")
                        print(now.strftime("%Y-%m-%d %H:%M"))
                        print("Switched lamp is switched off, turning controlled lamp off.")
                        set_status(b, lamps['Controlled'], 'off')
                        lamps_status = get_status(b, lamps)
                        display_status(lamps_status)
                        # Write to file
                        lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                        log_to_file(filename, lamps_file_output)
                        
                # if both the bedroom lamps have been turned off at the switch to make them both unreachable
                # this should be uncommon, as the controlled should always have power
                # Possible error!
                elif (not lamps_status['SwitchedR']) & (not lamps_status['ControlledR']):
                    Switched_was_unreachable = True
                    # if signal is also not reachable, continue but print warning to terminal
                    if not lamps_status['SignalR']:
                        print("")
                        print(f"{colors.fg.ryellow}Warning:{colors.reset} ALL lamps are unreachable!")
                        print("")
                    # only Switched and controlled are unreachable
                    else:
                        print("")
                        print(f"{colors.fg.ryellow}Warning:{colors.reset} Switched and Controlled lamps are unreachable!")
                        print("")
                
                # if only the controlled lamp has been turned off at the switch to make it unreachable
                # this should be uncommon, as the controlled should always have power
                # treat like normal Switched is reachable but Controlled will not turn on
                elif (lamps_status['SwitchedR']) & (not lamps_status['ControlledR']):
                    # if Switched is on
                    if (lamps_status['SwitchedO']):
                        # if this is the first time the Switched is reachable and on, turn on Signal
                        if Switched_was_unreachable:
                            # turn on the Signal
                            set_status(b, lamps['Signal'], 'on')
                            lamps_status = get_status(b, lamps)
                            Switched_was_unreachable = False
                            
                            # since we don't know the status of the Controlled, log as if Controlled had been off
                            print("")
                            print(now.strftime("%Y-%m-%d %H:%M"))
                            print("Switched lamp is on.")
                            # if signal is also not reachable, continue but print warning to terminal
                            if not lamps_status['SignalR']:
                                print("")
                                print(f"{colors.fg.ryellow}Warning:{colors.reset} Signal and Controlled lamps are unreachable!")
                                print("")
                            # only Controlled is unreachable
                            else:
                                print("")
                                print(f"{colors.fg.ryellow}Warning:{colors.reset} Controlled lamp is unreachable!")
                                print("")
                            
                            #set_status(b, lamps['Controlled'], 'on')
                            display_status(lamps_status)
                            # Write to file
                            lamps_file_output = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M")] + list(lamps_status.values())
                            log_to_file(filename, lamps_file_output)
                        # Switched has been on, print info about Controlled
                        else:
                            print("")
                            print(f"{colors.fg.ryellow}Warning:{colors.reset} Controlled lamp is unreachable!")
                            print("")
                    # if Switched is off, do nothing but print warning about the Controlled
                    else:
                        print("")
                        print(f"{colors.fg.ryellow}Warning:{colors.reset} Controlled lamp is unreachable!")
                        print("")
                    

if __name__ == "__main__":
    main()
