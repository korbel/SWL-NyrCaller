import time
import os
import re
import traceback
import sys
import queue
import win32com.client
import pythoncom

from threading import Thread
from datetime import datetime



rewind_mode = 'rewind' in sys.argv[1:]
trace_mode = 'trace' in sys.argv[1:]
last_date = datetime.min

tts_engine = None
announcement_queue = queue.PriorityQueue()

log_line_pattern = re.compile(r'\[(?P<date_string>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})Z.+?\].*?Scaleform\.Nyr10Caller - (?P<event_type>\w+)(: (?P<params>.+))?')

game_state = None
is_nyr10_active = False
dynels = {}
lurker_id = None

def reset_game_state():
    global game_state
    print(last_date.isoformat(), 'DEBUG', 'Reset')
    game_state = {
        'lurker_hp': 35158992,
        'lurker_targetable': True,

        'shadow1_call': False,
        'ps1_call': False,
        'ps2_call': False,
        'ps3_call': False,
        'fr_call': False,

        'shadow1_stop_dps_call': False,
        'ps1_stop_dps_call': False,
        'ps2_stop_dps_call': False,
        'ps3_stop_dps_call': False,

        'pod_targets': [],
        'number_of_birds': 0,
        'number_of_downfalls': 0,

        'lurker_became_targetable_at': None,
        'last_pod': None,
        'needs_to_report_filth': True,

        'command_ends': 0,
        'command_starts': 0
    }

def get_phase():
    if not game_state or not game_state['lurker_hp']:
        return 0
    elif game_state['lurker_hp'] > 26369244:
        return 1
    elif not game_state['lurker_targetable']:
        return 2
    else:
        return 3

def event_play_field_changed(playfield_id, playfield_name):
    global is_nyr10_active
    global dynels
    global lurker_id

    if playfield_id == '5715' and not is_nyr10_active:
        say('Welcome to New York raid E 10! The current local time is mid-afternoon.')
        is_nyr10_active = True
        print(last_date.isoformat(), 'DEBUG', 'Entered NYR E10')
    elif playfield_id != '5715' and is_nyr10_active:
        reset_game_state()
        is_nyr10_active = False
        dynels = {}
        lurker_id = None
        print(last_date.isoformat(), 'DEBUG', 'Left NYR E10')

    
def event_dynel_subscribed(character_id, character_name):
    global lurker_id

    if character_name == 'The Unutterable Lurker':
        if lurker_id and lurker_id != character_id:
            reset_game_state()
        lurker_id = character_id
        print(last_date.isoformat(), 'DEBUG', 'Lurker subscribed with ID ' + lurker_id)

    dynels[character_id] = {
        'name': character_name,
        'command': None
    }

    if character_name == 'Eldritch Guardian':
        game_state['number_of_birds'] += 1
        print(last_date.isoformat(), 'DEBUG', "Bird count since last reset: " + str(game_state['number_of_birds']))
        if game_state['number_of_birds'] == 3:
            say("Third bird")

def event_dynel_unsubscribed(character_id):
    global lurker_id

    if character_id == lurker_id:
        # lurker_id = None
        pass

    if character_id in dynels:
        del dynels[character_id]

def event_stat_changed(character_id, stat_id, value):
    if character_id == lurker_id:
        if stat_id == '27':
            new_hp = int(value)
            if game_state['lurker_hp'] < new_hp:
                reset_game_state()
            if not game_state['shadow1_call'] and new_hp < 26569244: # 26369244
                game_state['shadow1_call'] = True
                say("Shadow out of time soon!", True)
            if not game_state['ps1_call'] and new_hp < 24132320: # 23732320
                game_state['ps1_call'] = True
                say("Personal space soon!", True)
            if not game_state['ps2_call'] and new_hp < 16221546: # 15821546
                game_state['ps2_call'] = True
                say("Personal space soon!", True)
            if not game_state['ps3_call'] and new_hp < 9189478: # 8789478
                game_state['ps3_call'] = True
                say("Personal space soon!", True)
            if not game_state['fr_call'] and new_hp < 2157950: # 1757950
                game_state['fr_call'] = True
                say("Final resort soon!", True)

            if not game_state['shadow1_stop_dps_call']:
                if new_hp < 27400000 and not game_state['last_pod']:
                    say("Stop DPS and wait for pod", True)
                    game_state['shadow1_stop_dps_call'] = True

            game_state['lurker_hp'] = new_hp
        
        elif stat_id == '1050':
            if value == '3':
                print(last_date.isoformat(), 'DEBUG', 'Lurker became targetable')
                game_state['lurker_targetable'] = True
                if get_phase() == 3:
                    game_state['lurker_became_targetable_at'] = last_date

            elif value == '5':
                print(last_date.isoformat(), 'DEBUG', 'Lurker became untargetable')
                game_state['lurker_targetable'] = False

def event_character_died(character_id):
    pass

def event_character_alive(character_id):
    pass

def event_buff_added(character_id, buff_id, buff_name):
    if buff_name == 'Inevitable Doom':
        name = dynels[character_id]['name'] if character_id in dynels else 'an unknown person'
        game_state['pod_targets'].append(name)

        print(last_date.isoformat(), 'DEBUG', 'Pod target found: ' + character_id, name)
        print(last_date.isoformat(), 'DEBUG', 'Current targets: ' + str(game_state['pod_targets']))
        print(last_date.isoformat(), 'DEBUG', 'Current game phase: ' + str(get_phase()))

        if get_phase() == 1 or get_phase() == 3 and len(game_state['pod_targets']) >= 2:
            if len(game_state['pod_targets']) == 1:
                say('Pod target is ' + game_state['pod_targets'][0])
            else:
                say('Pod targets are ' + ', '.join(game_state['pod_targets'][:-1]) + ' and ' + game_state['pod_targets'][-1])
            game_state['pod_targets'] = []

def event_buff_updated(character_id, buff_id):
    pass

def event_buff_removed(character_id, buff_id):
    pass

def event_command_started(character_id, command_name):
    if character_id not in dynels:
        return

    if dynels[character_id] and dynels[character_id]['command'] and command_name == dynels[character_id]['command'][1]:
        return

    dynels[character_id]['command'] = (last_date, command_name)

    if lurker_id == character_id:
        game_state['command_starts'] += 1

        if command_name == 'Pure Filth' and game_state['needs_to_report_filth']:
            say("Filth is out")
            game_state['needs_to_report_filth'] = False
        elif command_name == 'Shadow Out Of Time':
            game_state['needs_to_report_filth'] = True
            if get_phase() == 3 and game_state['lurker_became_targetable_at']:
                say("Shadow out of time")
                print(last_date.isoformat(), 'DEBUG', 'Last pod timedelta is ' + str((last_date - game_state['last_pod']).total_seconds()))
                print(last_date.isoformat(), 'DEBUG', 'Shadow out of time P3 timedelta is ' + str((last_date - game_state['lurker_became_targetable_at']).total_seconds()))
                print(last_date.isoformat(), 'DEBUG', 'number of command ends: ', game_state['command_ends'])
                print(last_date.isoformat(), 'DEBUG', 'number of command starts: ', game_state['command_starts'])
        elif command_name.startswith('From Beneath'):
            say("Pod")
            game_state['last_pod'] = last_date
        elif command_name == 'Personal Space' or command_name == 'Final Resort':
            game_state['needs_to_report_filth'] = True

    if command_name == 'Downfall' and game_state['number_of_birds'] == 3:
        game_state['number_of_downfalls'] += 1
        print(last_date.isoformat(), 'DEBUG', 'Downfall count: ' + str(game_state['number_of_downfalls']))
        if game_state['number_of_downfalls'] == 3:
            say('Kill it')
        else:
            say(str(game_state['number_of_downfalls']))


def event_command_ended(character_id):
    if lurker_id == character_id:
        game_state['command_ends'] += 1

    if character_id not in dynels or not dynels[character_id]['command']:
        return

    #(start_date, command_name) = dynels[character_id]['command']
    # command ended
    dynels[character_id]['command'] = None


##########################
## File processing code ##
##########################

def process(line):
    global last_date

    m = log_line_pattern.match(line.strip())
    if not m:
        return
    
    last_date = datetime.fromisoformat(m.group('date_string'))
    event = m.group('event_type')
    params = m.group('params').split('|')

    if trace_mode:
        print(last_date.isoformat(), 'TRACE', event, params)

    if event == 'PlayFieldChanged':
        event_play_field_changed(*params)
    elif event == 'DynelSubscribed':
        event_dynel_subscribed(*params)
    elif event == 'DynelUnsubscribed':
        event_dynel_unsubscribed(*params)
    elif event == 'StatChanged':
        event_stat_changed(*params)
    elif event == 'CharacterDied':
        event_character_died(*params)
    elif event == 'CharacterAlive':
        event_character_alive(*params)
    elif event == 'BuffAdded':
        event_buff_added(*params)
    elif event == 'BuffRemoved':
        event_buff_removed(*params)
    elif event == 'BuffUpdated':
        event_buff_updated(*params)
    elif event == 'InvisibleBuffAdded':
        event_buff_added(*params)
    elif event == 'InvisibleBuffUpdated':
        event_buff_updated(*params)
    elif event == 'CommandStarted':
        event_command_started(*params)
    elif event == 'CommandEnded':
        event_command_ended(*params)
    elif event == 'CommandAborted':
        event_command_ended(*params)
    else:
        print(last_date.isoformat(), 'ERROR', 'Unsupported event:', event)

def follow(file_path):
    with open(file_path, 'r') as f:
        if not rewind_mode:
            f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                if rewind_mode:
                    return
                if f.tell() > os.path.getsize(file_path):
                    f.seek(0, 2)
                    continue
                time.sleep(0.1)
                continue
            yield line

def say(text, priority=False):
    print(last_date.isoformat(), 'ANNOUNCEMENT', text)
    if not rewind_mode:
        announcement_queue.put((0 if priority else 1, last_date, text))

def tts_loop():
    pythoncom.CoInitialize()
    tts = win32com.client.Dispatch('SAPI.SPVoice')

    if 'redirectOutput' in sys.argv[1:]:
        for i in range(tts.GetAudioOutputs().Count):
            token = tts.GetAudioOutputs().Item(i)
            if token.GetDescription() == 'CABLE Input (VB-Audio Virtual Cable)':
                tts.AudioOutput = token
                break
        else:
            print('ERROR', 'Could not find CABLE Input (VB-Audio Virtual Cable) audio device, playing to Default device')

    name = next((x.split('=', 1)[1] for x  in sys.argv[1:] if x.startswith('voice=')), None)
    if name:
        voices = tts.GetVoices(f"Name = {name}")
        if voices.Count > 0:
            tts.Voice = voices.Item(0)

    speed = next((x.split('=', 1)[1] for x  in sys.argv[1:] if x.startswith('speed=')), None)
    if speed:
        tts.Rate = int(speed)

    tts.Speak("Text-to-speach engine test.")
    while True:
        (_, _, text) = announcement_queue.get()
        tts.Speak(text)

def main():
    reset_game_state()
    log_file = next((x.split('=', 1)[1] for x  in sys.argv[1:] if x.startswith('log=')), os.path.join('..', 'ClientLog.txt'))
    log = follow(log_file if os.path.isabs(log_file) else os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file))
    if not rewind_mode:
        Thread(target=tts_loop, daemon=True).start()

    try:
        for line in log:
            process(line)
    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        pass

main()