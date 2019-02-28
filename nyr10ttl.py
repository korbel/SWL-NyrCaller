import time
import os
import re
import traceback
import sys
import queue
import win32com.client
import pythoncom

from threading import Thread
from datetime import datetime, timedelta



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
number_of_players = 0

def reset_game_state():
    global game_state
    debug('Reset')
    game_state = {
        'lurker_hp': 35158992,
        'lurker_targetable': True,
        'phase': 1,

        'shadow1_call': False,
        'early_ps_call': False,
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
        'start_time': None,
        'last_pod': None,
        'last_filth': None,
        'needs_to_report_filth': True,

        'command_ends': 0,
        'command_starts': 0,

        'players_died': 0,
        'dps': None
    }

def is_player(dynel_id):
    return int(dynel_id.split(':')[1]) >= 1<<24

def get_call_hp(stop_dps = False):
    if not game_state['dps']:
        return None
    # P1 call 1 sec early and Stop dps 6 sec early
    # P3 DPS should be around 2.5 times of P1 DPS
    dps_factor = game_state['dps'] * 1
    stop_dps_factor = 6 if stop_dps else 1
    phase_factor = 1 if game_state['phase'] < 3 else 2.5
    player_number_factor = calculate_player_number_factor()
    return stop_dps_factor * phase_factor * player_number_factor * dps_factor

def calculate_player_number_factor():
    players_died = game_state['players_died']
    if players_died == 0:
        return 1

    number_of_non_dps = 3
    number_of_dps = number_of_players - number_of_non_dps

    non_dps_factor = 0.3 
    
    dps_factor_total = number_of_dps + number_of_non_dps * non_dps_factor

    if players_died <= number_of_dps:
        return (dps_factor_total - players_died) / dps_factor_total
    else:
        return (number_of_players - players_died) * non_dps_factor


#######################
## Events start here ##
#######################

def event_play_field_changed(playfield_id, playfield_name):
    global is_nyr10_active
    global dynels
    global lurker_id

    if playfield_id == '5715' and not is_nyr10_active:
        say('Welcome to New York raid E 10!')
        is_nyr10_active = True
        debug('Entered NYR E10')
    elif playfield_id != '5715' and is_nyr10_active:
        reset_game_state()
        is_nyr10_active = False
        dynels = {}
        lurker_id = None
        debug('Left NYR E10')

    
def event_dynel_subscribed(character_id, character_name):
    global lurker_id
    global number_of_players

    if character_name == 'The Unutterable Lurker':
        if lurker_id and lurker_id != character_id:
            reset_game_state()
        lurker_id = character_id
        debug('Lurker subscribed with ID ' + lurker_id)

    if is_player(character_id):
        number_of_players += 1

    dynels[character_id] = {
        'name': character_name,
        'command': None
    }

    if character_name == 'Eldritch Guardian':
        game_state['number_of_birds'] += 1
        debug("Bird count since last reset: " + str(game_state['number_of_birds']))
        if game_state['number_of_birds'] == 3:
            say("Third bird")

def event_dynel_unsubscribed(character_id):
    global number_of_players

    if is_player(character_id):
        number_of_players -= 1

    if character_id in dynels:
        del dynels[character_id]

def event_stat_changed(character_id, stat_id, value):
    if character_id == lurker_id:
        if stat_id == '27':
            new_hp = int(value)

            if not game_state['dps'] and new_hp < 30000000:
                damage = 35158992 - new_hp
                seconds = (last_date - game_state['start_time']).total_seconds()
                game_state['dps'] = damage / seconds
                debug(f'DPS calculated in {seconds} seconds: ' + str(game_state['dps']))

            if game_state['lurker_hp'] < new_hp:
                reset_game_state()

            if game_state['dps']:
                if not game_state['shadow1_call'] and new_hp < 26369244 + (get_call_hp() if not game_state['shadow1_stop_dps_call'] else 0):
                    game_state['shadow1_call'] = True
                    say("Shadow out of time soon!", True)
                if not game_state['ps1_call'] and new_hp < 23732320 + get_call_hp() * 0.4:
                    if not game_state['lurker_became_targetable_at']:
                        if not game_state['early_ps_call']:
                            game_state['early_ps_call'] = True
                            say("Personal space will be early")
                    elif (last_date - game_state['lurker_became_targetable_at']).total_seconds() > 7:    
                        game_state['ps1_call'] = True
                        say("Personal space soon!", True)
                if not game_state['ps2_call'] and new_hp < 15821546 + get_call_hp():
                    game_state['ps2_call'] = True
                    say("Personal space soon!", True)
                if not game_state['ps3_call'] and new_hp < 8789478 + get_call_hp():
                    game_state['ps3_call'] = True
                    say("Personal space soon!", True)
                if not game_state['fr_call'] and new_hp < 1757950 + get_call_hp():
                    game_state['fr_call'] = True
                    say("Final resort soon!", True)
                if not game_state['shadow1_stop_dps_call'] and game_state['start_time']:
                    last_pod = game_state['last_pod'] if game_state['last_pod'] else game_state['start_time'] + timedelta(seconds=16)
                    seconds_till_next_pod = 32 - (last_date - last_pod).total_seconds()

                    if new_hp < 26369244 + get_call_hp(True):
                        if seconds_till_next_pod < 9: # call HP should cover around 6 seconds, +3 sec should be safe ... maybe
                            say("Stop DPS and wait for pod", True)
                        elif seconds_till_next_pod < 12:
                            say("Push it")
                        game_state['shadow1_stop_dps_call'] = True

            game_state['lurker_hp'] = new_hp
        
        elif stat_id == '1050':
            if value == '3':
                debug('Lurker became targetable')
                game_state['lurker_targetable'] = True
                if game_state['phase'] == 2:
                    game_state['phase'] = 3
                    game_state['lurker_became_targetable_at'] = last_date
                    game_state['last_pod'] = last_date
                    game_state['needs_to_report_filth'] = True

            elif value == '5':
                debug('Lurker became untargetable')
                game_state['lurker_targetable'] = False

def event_character_died(character_id):
    if is_player(character_id) and character_id in dynels:
        game_state['players_died'] += 1


def event_character_alive(character_id):
    if not game_state['start_time']:
        game_state['players_died'] = max(game_state['players_died'] - 1, 0)

def event_buff_added(character_id, buff_id, buff_name):
    if buff_name == 'Inevitable Doom':
        name = dynels[character_id]['name'] if character_id in dynels else 'an unknown person'
        game_state['pod_targets'].append(name)

        debug('Pod target found: ' + character_id, name)
        debug('Current targets: ' + str(game_state['pod_targets']))
        debug('Current game phase: ' + str(game_state['phase']))

        if game_state['phase'] == 1 or game_state['phase'] == 3 and len(game_state['pod_targets']) >= 2:
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

        if command_name == 'Pure Filth':
            if not game_state['last_filth']:
                game_state['start_time'] = last_date - timedelta(seconds=1)
                debug("Start time: ", game_state['start_time'].isoformat())
            if game_state['needs_to_report_filth']:
                say("Filth is out")
                game_state['needs_to_report_filth'] = False
            game_state['last_filth'] = last_date
        elif command_name == 'Shadow Out Of Time':
            if game_state['phase'] == 1:
                game_state['phase'] = 2

            if game_state['phase'] == 3 and game_state['lurker_became_targetable_at']:
                say("Shadow out of time")
                debug('Last pod timedelta is ' + str((last_date - game_state['last_pod']).total_seconds()))
                debug('Shadow out of time P3 timedelta is ' + str((last_date - game_state['lurker_became_targetable_at']).total_seconds()))
                debug('number of command ends: ', game_state['command_ends'])
                debug('number of command starts: ', game_state['command_starts'])
        elif command_name.startswith('From Beneath'):
            say("Pod")
            game_state['last_pod'] = last_date
        elif command_name == 'Personal Space' or command_name == 'Final Resort':
            debug(command_name)

    if command_name == 'Downfall' and game_state['number_of_birds'] == 3:
        game_state['number_of_downfalls'] += 1
        debug('Downfall count: ' + str(game_state['number_of_downfalls']))
        if game_state['number_of_downfalls'] == 3:
            say('Kill it')
        else:
            say(str(game_state['number_of_downfalls']))


def event_command_ended(character_id):
    if lurker_id == character_id:
        game_state['command_ends'] += 1

    if character_id not in dynels or not dynels[character_id]['command']:
        return

    (start_date, command_name) = dynels[character_id]['command']
    
    # if lurker_id == character_id:
    #    if command_name == 'Personal Space' or command_name == 'Final Resort':
    #        if not game_state['needs_to_report_filth'] and game_state['last_filth'] and (last_date - game_state['last_filth']).total_seconds() >= 15:
    #            game_state['needs_to_report_filth'] = True
    #            say("Wait for filth")

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

    trace(event, params)

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
        error('Unsupported event:', event)

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
    pythoncom.CoInitialize() # pylint: disable=no-member
    tts = win32com.client.Dispatch('SAPI.SPVoice')

    if 'redirectOutput' in sys.argv[1:]:
        for i in range(tts.GetAudioOutputs().Count):
            token = tts.GetAudioOutputs().Item(i)
            if token.GetDescription() == 'CABLE Input (VB-Audio Virtual Cable)':
                tts.AudioOutput = token
                break
        else:
            error('Could not find CABLE Input (VB-Audio Virtual Cable) audio device, playing to Default device')

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

def debug(*args):
    print(last_date.isoformat(), 'DEBUG', *args)
def error(*args):
    print(last_date.isoformat(), 'ERROR', *args)
def trace(*args):
    if trace_mode:
        print(last_date.isoformat(), 'TRACE', *args)

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