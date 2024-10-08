import time

import pygame
import socket
import ipaddress
import argparse
import sys

from utils.helper_functions import *
from utils.gamepad_mapping import *
from utils.xbox_reports import XBOX_REPORT

import colorama
colorama.init()

RESTART = 'shift+R'
QUIT = 'shift+Q'
REMAP = 'shift+M'


def get_parsed_args():
    # Create an argument parser
    parser = argparse.ArgumentParser(description='Send joystick data to a computer over tcp/ip')

    # Add arguments to the parser
    parser.add_argument('-n', '--host', type=str, help='IP address of host/server')
    parser.add_argument('-p', '--port', type=str, help='Port that the host/server is listening on')
    parser.add_argument('-f', '--fps', type=str,
                        help='How many times the client will attempt to communicate with server per second')
    parser.add_argument('-m', '--mode', type=int, help='Operational Mode: 1: pymaps, 2: ds4 passthrough, 3: hidmaps')
    parser.add_argument('-l', '--latency', action='store_true', help='Show latency output')
    parser.add_argument('-s', '--select', action='store_true', help='Show select input menu')
    parser.add_argument('-a', '--auto', type=bool, help='set to true or false for auto select input')

    # Parse and return the arguments
    return parser.parse_args()


def get_arg_settings(args):
    # set port
    if args.port:
        PORT = int(args.port)
    else:
        PORT = 5000
    # set fps
    if args.fps:
        TARGET_FPS = int(args.fps)
    else:
        TARGET_FPS = 30
    # OPS_MODE 1: pymaps, 2: ds4 passthrough, 3: hidmaps
    if args.mode:
        OPS_MODE = args.mode
    else:
        OPS_MODE = 1
    # set auto select
    if args.auto:
        AUTO_SELECT = args.auto
    else:
        AUTO_SELECT = False

    return PORT, TARGET_FPS, OPS_MODE, AUTO_SELECT


def wait_for_no_keyboard_input():
    while True:
        if not keyboard.is_pressed('shift') and not keyboard.is_pressed('M') \
                and not keyboard.is_pressed('R') and not keyboard.is_pressed('1') \
                and not keyboard.is_pressed('2') and not keyboard.is_pressed('3'):
            return 1


def select_device(op_mode, auto_select):
    vendor_id = product_id = None
    # if passthrough_mode attempt auto select ps4 controller
    if op_mode == 2:
        gamepad, vendor_id, product_id = select_hid_device([d for d in hid.enumerate() if d['product_id'] == 2508])
        if not gamepad:
            gamepad, vendor_id, product_id = select_hid_device(hid.enumerate(), 0, 'PyGame Device')
            if gamepad == -1:
                op_mode = 1
                auto_select = 0

    if op_mode == 3:
        gamepad, vendor_id, product_id = select_hid_device(hid.enumerate(), 0, 'PyGame Device')
        if gamepad == -1:
            op_mode = 1
            auto_select = 0

    # else run pygame mode
    if op_mode == 1:
        pygame.init()
        # User selects gamepad
        # if auto is off select with other option
        gamepad = select_pygame_device(pygame, auto_select, 'Another Device (HID)')
        # if no gamepads attached quit
        if gamepad is None:
            sys.exit()
        # if other picked set hid mode and select device
        if gamepad == -1:
            gamepad, vendor_id, product_id = select_hid_device(hid.enumerate())
            op_mode = 3
        if not gamepad:
            sys.exit()

    return gamepad, op_mode, vendor_id, product_id


def flush_HID_buffer(gamepad, clock, ds4_data_offset):
    # clear the read buffer of any unread values
    # this is important so that we don't read old values from the device

    # hidapi has no flush so this function acts as the frame limiter
    # while reading reports to keep them as current as possible
    current_time = time.monotonic()
    elapsed_time = current_time - clock.last_frame_time
    sleep_time = clock.target_frame_time - elapsed_time

    if ds4_data_offset == 3:
        if sleep_time > 0:  # works well when connected via BT but causes input delay when connected via USB
            pygame.time.wait(int(sleep_time - DS4_REPORTING_DELAY))
            data = gamepad.read(64)
            pygame.time.wait(int(DS4_REPORTING_DELAY))
    else:
        # produces inaccurate (higher) frame rate but no input delay on USB
        for x in range(int(sleep_time / DS4_REPORTING_DELAY)-1):
            data = gamepad.read(64)
            pygame.time.wait(int(DS4_REPORTING_DELAY))

    clock.last_frame_time = current_time
    clock.frame_count += 1


def get_host_address():
    # request server ip address
    while True:
        if not args.host:
            host_address = input("Please enter the host ip address (or nothing for localhost): ")
        else:
            host_address = args.host
        if not host_address:
            host_address = "127.0.0.1"
        try:
            ipaddress.ip_address(host_address)
            break
        except ValueError:
            print("Invalid IP address. Please try again.")
            args.host = ''
    return host_address


def establish_connection(ip_address, op_mode):
    # establish client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (ip_address, PORT)
    try:
        client_socket.connect(server_address)
        client_socket.sendall(str(f'{TARGET_FPS}:{op_mode}').encode())
        response = client_socket.recv(1024)
    except Exception:
        print("<< Connection Failed >>")
        return False

    print("Connected!")

    return client_socket


def activate_ds4_extended_reports(gamepad, ds4_data_offset):
    if ds4_data_offset == 1:
        # READ USB CALIBRATE REPORT 0x02 // size is 37 bytes
        gamepad.get_feature_report(0x02, 37)
        return 1
    elif ds4_data_offset == 3:
        # READ BT CALIBRATE REPORT 0x05 // size is 41 bytes
        gamepad.get_feature_report(0x05, 41)
        return 1
    return 0


def joySender(operational_mode, auto_select):
    clock = FpsLimiter(TARGET_FPS)
    failed_connections = 0
    sleep_time = 0
    start_time = 0
    last_output = time.monotonic()
    vendor_id = product_id = None
    buttons = None
    map_name = None
    report_size = None
    xbox_report = XBOX_REPORT()

    ###########################################################################
    # User or auto select gamepad and receive Operating Mode update and some device info
    gamepad, operational_mode, vendor_id, product_id = select_device(operational_mode, auto_select)

    ###########################################################################
    # Set up Button Mapping for Operating Mode
    if operational_mode == 3:
        print(f'HID Mode Activated')
        buttons = HIDButtonMapping()
        map_name = f'{hex(vendor_id)}{hex(product_id)}'
    elif operational_mode == 2:
        print(f'DS4 Full Motion Mode Activated')
        # first byte is used to determine where stick input starts
        ds4_data_offset = 3 if gamepad.read(64)[0] == 0x11 else 1

        # activate extended ds4 reports
        result = activate_ds4_extended_reports(gamepad, ds4_data_offset)

        # cant seem to get the writing of output reports to work through python
        '''
        # set lightbar color values
        ds4_output_report[8] = 0  # R
        ds4_output_report[9] = 4    # G
        ds4_output_report[10] = 255  # B

        # Copy the contents of array2 to array1 starting from index 3
        # ds4_output_report[3:3+len(ds4_bt_state_data)] = ds4_bt_state_data

        byte_array = [
            0x11, 0xc0, 0x20, 0xf3, 0x04, 0x00, 0x00, 0x00, 0x00, 0x04, 0xff, 0x00, 0x00, 0x00, 0x00, 0xfb,
            0x7f, 0x00, 0x00, 0xd0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x48, 0xf5, 0xd9, 0x13, 0xae,
            0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x5b, 0x05, 0x3f, 0xbc, 0xfb,
            0x7f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x43, 0x4b, 0x43, 0x48, 0xf6, 0x7f,
            0x00, 0x00, 0xd0, 0x0a, 0x45, 0x48, 0xf6, 0x7f, 0x00, 0x00, 0xb0, 0xf5, 0x00, 0x00, 0x00, 0x03,
        ]

        result = gamepad.write(byte_array)
        print(result)
        '''
    else:
        print(f'PyGame Mode Activated')
        buttons = PyGameButtonMapping()
        map_name = f'{encode_string_to_hex(gamepad.get_name())}'

    ###########################################################################
    # If not in DS4 Passthrough mode look for saved mapping or create one
    if operational_mode != 2:
        # Look for an existing map for selected device
        map_check = check_for_saved_mapping(map_name)
        # Load map if it exists
        if map_check[0]:
            print("Loading Saved Button Map")
            # Load button map for known device
            buttons.load_button_maps(map_check[1])
        else:
            print("Create Button Map For Selected Device ...")
            # Create a map for all inputs
            if operational_mode == 3:
                set_hid_mapping(gamepad, buttons, [])
            else:
                set_pygame_mapping(pygame, gamepad, buttons, [])
            # Save mapping to %APPDATA%/APP_NAME/map_name
            buttons.save_button_maps(map_check[1])

        # Build Input Lists
        input_list = buttons.get_set_button_names()
        if operational_mode == 3:
            hid_input_lists = get_hidmap_input_lists(buttons, input_list)
            report_size = len(gamepad.read(64))

    ###########################################################################
    # Main Loop keeps client running
    # asks for new host if connection fails 3 times
    while True:
        client_socket = establish_connection(get_host_address(), operational_mode)
        loop_count = 0
        while client_socket:
            # Shift+R will reset program allowing joystick reconnection/selection
            # Shift+M will remap all buttons on a hid or pygame device
            # Shift+Q will exit the program
            if keyboard.is_pressed(RESTART) \
                    or keyboard.is_pressed(REMAP) \
                    or keyboard.is_pressed(QUIT):
                client_socket.close()
                break

            ###################################
            # Read from Input
            if operational_mode == 3:
                # Read the next HID report
                # input_report = gamepad.read(report_size)
                # set the XBOX REPORT from HID input_report
                get_xbox_report_from_hidmap(gamepad, report_size, buttons, hid_input_lists, xbox_report)
            elif operational_mode == 2:
                # Read the next HID report (64 bytes) for DS4 Passthrough
                input_report = gamepad.read(64)
            else:
                # set the XBOX REPORT from PyGame inputs
                get_xbox_report_from_pymap(pygame, gamepad, buttons, input_list, xbox_report)

            ###################################
            # let's calculate some latency
            if args.latency and loop_count == 19:
                #start_time = time.time()
                start_time = time.monotonic()

            ###################################
            # Send joystick input to server
            try:
                if operational_mode == 2:
                    # Shift bytearray to index of first stick value
                    client_socket.sendall(bytes(input_report)[ds4_data_offset:])
                else:
                    client_socket.sendall(package_xbox_report(xbox_report))
            except Exception:
                print("<< Connection Lost >>")
                client_socket.close()
                break
            ###################################
            # Wait for server response
            try:
                response = client_socket.recv(1024)
            except Exception:
                print(f"<< Connection Lost >>")
                client_socket.close()
                break

            if args.latency:
                loop_count += 1
                if loop_count == 20:
                    end_time = time.monotonic()  # 20 round trips completed
                    test = (end_time - last_output)
                    print(f"fps:{(clock.frame_count/(end_time - last_output)): .2f} \tLatency: {(end_time - start_time):.5f} ms")
                    # Move the cursor up by 1 line
                    print("\033[1A", end="")
                    loop_count = 0
                    clock.frame_count = 0
                    last_output = end_time


            ##################################
            ## **  Process Rumble Feedback data
            # Interpret the first two bytes or response as uint8
            left, right = struct.unpack('BB', response[:2])
            if update_rumble('L', left) or update_rumble('R', right):
                if operational_mode == 2:
                    #SetDS4RumbleValue(byte(buffer[0]), byte(buffer[1]));
                    #allGood = SendDS4Update();
                    ds4_output_report[6] = left
                    ds4_output_report[7] = right
                    gamepad.write(ds4_output_report)

                    pass
                elif operational_mode == 1:
                    pygame_rumble(gamepad, left, right)

            # set clock to limit FPS
            if operational_mode == 2:
                # flush input buffer for up-to-date reports
                flush_HID_buffer(gamepad, clock, ds4_data_offset)
            else:
                clock.tick()

        # Shift+R will reset program allowing joystick reconnection/selection, holding a number will change op mode
        if keyboard.is_pressed(RESTART):
            while keyboard.is_pressed(RESTART):
                pass
            if keyboard.is_pressed('1'):
                return 2
            if keyboard.is_pressed('2'):
                return 3
            if keyboard.is_pressed('3'):
                return 4
            return 1
        # Shift+M will re-map all inputs
        if keyboard.is_pressed(REMAP):
            if operational_mode == 3:
                set_hid_mapping(gamepad, buttons, [])
            else:
                set_pygame_mapping(pygame, gamepad, buttons, [])
            buttons.save_button_maps(map_check[1])
        # Shift+Q will quit
        if keyboard.is_pressed(QUIT):
            return 0

        ###################################
        # Connection has failed or been aborted
        failed_connections += 1
        if failed_connections > 3:
            args.host = ''
            failed_connections = 0


# ENTRY POINT STARTS HERE
args = get_parsed_args()
PORT, TARGET_FPS, OPS_MODE, AUTO_SELECT = get_arg_settings(args)
RUN = True
while RUN:
    RUN = joySender(OPS_MODE, AUTO_SELECT)
    if RUN > 1:
        OPS_MODE = RUN - 1
        AUTO_SELECT = False
        wait_for_no_keyboard_input()
