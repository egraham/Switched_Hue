# Switched_Hue

This script will monitor a 'Switched' hue lamp (one who's power will be turned on and off by a switch 
   and thus make the lamp unreachable if no power).  If the Switched is switched (powered) on, then this script will
   turn on a 'Controlled' lamp (a "slave" to the Switched) and a 'Signal' lamp (both will turn on when Switched
   goes from unreachble to reachable).  This script will also turn on or off the Controlled lamp in parallel to the
   Switched (if it is programatically turned on or off, e.g., with the Hue app), but otherwise
   not change the Signal lamp.
   
This script will only function on a Windows machine (because of the keyboard capture, possibly other reasons) and 
   should be run in a command terminal (at least not in the Spyder console because key capture doesn't work, although
   it will run fine otherwise).
