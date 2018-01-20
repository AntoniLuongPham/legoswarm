#!/usr/bin/env python3

from camera_client import CameraUDP
import numpy as np
import time
import logging
#from hardware import DriveBase
from hardware_old import DriveBase
from springs import Spring

#################################################################
###### Init
#################################################################

try:
    from id import MY_ID
except:
    MY_ID = 3

# Log settings
logging.basicConfig(format='%(asctime)s, %(levelname)s, %(message)s',datefmt='%H:%M:%S', level=logging.WARNING)

# Start data thread
camera_thread = CameraUDP()
camera_thread.start()

# Activate hardware if we're a robot
base = DriveBase(left='outB', right='outC', wheel_diameter=0.043, wheel_span=0.12)

#################################################################
###### At every time step, read camera data, process it,
###### and steer robot accordingly
#################################################################

while True:
    #################################################################
    ###### Receive data
    #################################################################
    logging.debug("Loop start")
    loopstart = time.time()
    try:
        # Get robot positions and settings from server
        data = camera_thread.get_data()
        neighbor_info, robot_settings = data['neighbor_info'][MY_ID], data['robot_settings']
        neighbors = neighbor_info.keys()
        spring_between_robots = Spring(robot_settings['spring_between_robots'])
    except:
        # Stop the loop if we're unable to get server data
        logging.warning("No data or the camera didn't see me. Waiting 1s")
        base.stop()
        time.sleep(1)
        continue
    logging.debug(str(time.time()-loopstart) + " Got data")

    #################################################################
    ###### Process received data
    #################################################################

    # For now, just behavior that makes robots avoid one another
    total_force = np.array([0, 0])
    for neighbor in neighbors:
        gripper_location = neighbor_info[neighbor]['gripper_location']
        total_force = total_force + spring_between_robots.get_force_vector(gripper_location)    

    #################################################################
    ###### Actuation based on processed data
    #################################################################

    # Decompose stretch into forward and sideways force
    forward_force, sideways_force = total_force

    logging.debug(str(time.time() - loopstart) + "Done spring calculations")

    # Obtain speed and turnrate
    # TODO: remove MINUS sign in turn rate below. Instead make CW/CCW a configurable option in drivebase
    speed = forward_force * robot_settings['speed_per_unit_force']
    turnrate = -sideways_force * robot_settings['turnrate_per_unit_force']

    # Drive!
    base.drive_and_turn(speed, turnrate)

    # Debug print of where we're going        
    logging.debug('speed: ' + str(speed) + ' turnrate: ' + str(turnrate))

    #################################################################
    ###### Pause and repeat
    #################################################################
    time.sleep(1)

#################################################################
###### Closing down and cleaning up
#################################################################
camera_thread.stop()