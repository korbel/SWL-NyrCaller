import time
import os
import re
import traceback
import sys
import queue
import win32com.client
import pythoncom
import math

from threading import Thread, Timer
from datetime import datetime, timedelta



rewind_mode = 'rewind' in sys.argv[1:]
trace_mode = 'trace' in sys.argv[1:]
last_date = last_real_date = datetime.min

tts_engine = None
announcement_queue = queue.PriorityQueue()

log_line_pattern = re.compile(r'\[(?P<date_string>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})Z.+?\].*?Scaleform\.Nyr10Caller - (?P<event_type>\w+)(: (?P<params>.+))?')

game_state = None
is_nyr10_active = False
dynels = {}
lurker_id_stack = []
last_lurker_id = None
number_of_players = 0

lurker_max_hp = 43199824
shadow1_hp = int(round(lurker_max_hp * 0.75))
ps_fr_hps = list(map(lambda percentage: int(round(lurker_max_hp * percentage)), (0.675, 0.45, 0.25, 0.05)))
start_dps_calc_hp = int(round(lurker_max_hp * 0.95))
stop_dps_calc_hp = int(round(lurker_max_hp * 0.81))
stop_dps_call_timing = 7
call_timing = 1

def reset_game_state():
    global game_state
    debug("Reset")
    game_state = {
        'lurker_hp': lurker_max_hp,
        'lurker_targetable': True,
        'phase': 1,

        'shadow1_call': False,
        'shadow1_stop_dps_call': False,
        'early_ps': False,
        'early_ps_call': False,
        'ps1_call': False,
        'ps1_stop_dps_call': False,
        'ps2_call': False,
        'ps2_stop_dps_call': False,
        'ps3_call': False,
        'ps3_stop_dps_call': False,
        'fr_call': False,
        'fr_stop_dps_call': False,

        'pod_targets': [],
        'birds': set(),
        'number_of_downfalls': 0,

        'lurker_became_targetable_at': None,
        'start_time': None,
        'start_of_dps_calc': None,
        'last_pod': None,
        'last_filth': None,
        'last_shadow': None,
        'last_pod_targeting': None,
        'ps_counter': 0,
        'needs_to_report_filth': True,

        'hulk_spawned': False,
        'hulk_focus_warn': False,

        'players_died': 0,
        'dps': None
    }

def get_lurker_id():
    if not lurker_id_stack:
        return None
    return lurker_id_stack[-1] 

def is_player(dynel_id):
    return int(dynel_id.split(':')[1]) >= 1<<24

def get_hp_eta(future_hp):
    dps = get_normalized_dps()

    if dps is None:
        return None

    if dps == 0:
        return math.inf
    
    return (game_state['lurker_hp'] - future_hp) / dps

def get_normalized_dps():
    if not game_state['dps']:
        return None

    phase_start_dps_modifier = 1
    if game_state['phase'] == 3:
        start_time = (last_date - game_state['lurker_became_targetable_at']).total_seconds()
        phase_start_dps_modifier = min(max(start_time - 4, 0) / 8, 1)

    phase_factor = 1 if game_state['phase'] < 3 else 2.5
    player_number_factor = calculate_player_number_factor()

    return phase_factor * player_number_factor * phase_start_dps_modifier * game_state['dps']

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

def start_p3(when = 0):
    game_state['phase'] = 3
    game_state['lurker_became_targetable_at'] = last_date + timedelta(seconds=when)
    game_state['last_pod'] = last_date
    game_state['needs_to_report_filth'] = True
    debug(f"P3 started at {game_state['lurker_became_targetable_at'].isoformat()} ({-when} seconds ago)")

def call_pod_targets():
    target_count = len(game_state['pod_targets'])
    if target_count == 0:
        return
    elif target_count == 1:
        say("Pod target is " + game_state['pod_targets'][0])
    else:
        say(f"Pod targets are {', '.join(game_state['pod_targets'][:-1])} and {game_state['pod_targets'][-1]}")
        # if 'Mei Ling' in game_state['pod_targets']:
            # say('Watch out for death trap')
    game_state['pod_targets'] = []

#######################
## Events start here ##
#######################

def event_play_field_changed(playfield_id, playfield_name):
    global is_nyr10_active
    global dynels
    global lurker_id_stack

    if playfield_id == '5715' and not is_nyr10_active:
        reset_game_state()
        say("Welcome to New York raid E 10!")
        is_nyr10_active = True
        debug("Entered NYR E10")

    elif playfield_id != '5715' and is_nyr10_active:
        is_nyr10_active = False
        dynels = {}
        lurker_id_stack = []
        debug("Left NYR E10")

    
def event_dynel_subscribed(character_id, character_name):
    global number_of_players

    if character_name == 'The Unutterable Lurker':
        current_lurker_id = get_lurker_id()
        if not current_lurker_id and last_lurker_id != character_id:
            reset_game_state()
        lurker_id_stack.append(character_id)
        debug("Lurker subscribed with ID", character_id)

    if character_id not in dynels:
        dynels[character_id] = {
            'name': character_name,
            'command': None
        }
        if is_player(character_id):
            number_of_players += 1

    if character_name == 'Eldritch Guardian' and character_id not in game_state['birds']:
        game_state['birds'].add(character_id)
        bird_count = len(game_state['birds'])
        debug("Bird count since last reset:", bird_count)
        if bird_count == 3:
            say("Third bird")

    if character_name == 'Zero-Point Titan' and not game_state['hulk_spawned']:
        game_state['hulk_spawned'] = True
        if game_state['phase'] == 3:
            say("Hulk has spawned")

def event_dynel_unsubscribed(character_id):
    global number_of_players
    global last_lurker_id

    if character_id in dynels:
        del dynels[character_id]
        if is_player(character_id):
            number_of_players -= 1

    if character_id in lurker_id_stack:
        current_lurker_id = get_lurker_id()
        if current_lurker_id != character_id:
            reset_game_state()
        lurker_id_stack.remove(character_id)
        last_lurker_id = character_id

def event_stat_changed(character_id, stat_id, value):
    if character_id == get_lurker_id():
        if stat_id == '27':
            new_hp = int(value)

            if not game_state['dps'] and new_hp < start_dps_calc_hp:
                if not game_state['start_of_dps_calc']:
                    if game_state['lurker_hp'] == lurker_max_hp:
                        return
                    game_state['start_of_dps_calc'] = (last_date, new_hp)
                if new_hp < stop_dps_calc_hp:
                    (calc_start_date, calc_start_hp) = game_state['start_of_dps_calc']
                    damage = calc_start_hp - new_hp
                    seconds = (last_date - calc_start_date).total_seconds()
                    game_state['dps'] = damage / seconds
                    debug(f"DPS calculated in {seconds} seconds: {game_state['dps']}")

            # if game_state['lurker_hp'] < new_hp == lurker_max_hp:
            #     reset_game_state()

            if game_state['dps'] and game_state['ps_counter'] < 4:
                dps = get_normalized_dps()

                if game_state['phase'] < 3 and dps and get_hp_eta(ps_fr_hps[0]) < 4:
                    game_state['early_ps'] = True

                if game_state['phase'] == 3:

                    phase_started = (last_date - game_state['lurker_became_targetable_at']).total_seconds() if game_state['lurker_became_targetable_at'] else math.inf

                    last_pod = (last_date - game_state['last_pod']).total_seconds() if game_state['last_pod'] else -math.inf
                    last_shadow = (last_date - game_state['last_shadow']).total_seconds() if game_state['last_shadow'] else -math.inf
                    # last_filth = (last_date - game_state['last_filth']).total_seconds() if game_state['last_filth'] else -math.inf

                    next_pod = 32 - last_pod if last_pod < phase_started else 32 - phase_started
                    next_shadow = max(100 - last_shadow if last_shadow < phase_started else 60 - phase_started, 20 - last_pod)
                    next_ps_fr = get_hp_eta(ps_fr_hps[game_state['ps_counter']])
                    # next_filth = max(18 - last_filth if last_filth < phase_started else phase_started, 10 - last_pod)

                    if stop_dps_call_timing - 2 < next_ps_fr < stop_dps_call_timing + 2:
                        shadow_ps_diff = next_shadow - next_ps_fr
                        should_call = game_state['ps_counter'] < 3 and -10 < shadow_ps_diff < 6
                        
                        if not game_state['ps1_stop_dps_call'] and game_state['ps_counter'] == 0:
                            if should_call:
                                say("Stop DPS", True)
                                debug("last_shadow", last_shadow, "next_shadow", next_shadow, "next_ps_fr", next_ps_fr)
                                game_state['ps1_stop_dps_call'] = True
                        if not game_state['ps2_stop_dps_call'] and game_state['ps_counter'] == 1:
                            if should_call:
                                say("Stop DPS", True)
                                debug("last_shadow", last_shadow, "next_shadow", next_shadow, "next_ps_fr", next_ps_fr)
                                game_state['ps2_stop_dps_call'] = True
                        if not game_state['ps3_stop_dps_call'] and game_state['ps_counter'] == 2:
                            if should_call:
                                say("Stop DPS", True)
                                debug("last_shadow", last_shadow, "next_shadow", next_shadow, "next_ps_fr", next_ps_fr)
                                game_state['ps3_stop_dps_call'] = True

                    if not game_state['fr_stop_dps_call'] and game_state['ps_counter'] == 3 and next_ps_fr < stop_dps_call_timing:
                        if next_pod < stop_dps_call_timing + 2:
                            # say("Stop DPS and wait for pod", True)
                            debug("next_pod", next_pod, "next_ps_fr", next_ps_fr)
                        game_state['fr_stop_dps_call'] = True

                    if next_ps_fr < call_timing:
                        if not game_state['ps1_call'] and game_state['ps_counter'] == 0: 
                            game_state['ps1_call'] = True
                            say("Personal space soon!", True)
                        if not game_state['ps2_call'] and game_state['ps_counter'] == 1:
                            game_state['ps2_call'] = True
                            say("Personal space soon!", True)
                        if not game_state['ps3_call'] and game_state['ps_counter'] == 2:
                            game_state['ps3_call'] = True
                            say("Personal space soon!", True)
                        if not game_state['fr_call'] and game_state['ps_counter'] == 3:
                            game_state['fr_call'] = True
                            say("Final resort soon!", True)

                    if not game_state['hulk_focus_warn'] and next_ps_fr < 4 and game_state['ps_counter'] < 3 and (last_shadow < 14 or game_state['hulk_spawned']):
                        say("Focus on hulk", True)
                        game_state['hulk_focus_warn'] = True

                if not game_state['shadow1_stop_dps_call'] and game_state['start_time']:
                    last_pod = game_state['last_pod'] if game_state['last_pod'] else game_state['start_time'] + timedelta(seconds=16)
                    seconds_till_next_pod = 32 - (last_date - last_pod).total_seconds()

                    if get_hp_eta(shadow1_hp) < stop_dps_call_timing :
                        if seconds_till_next_pod < stop_dps_call_timing + 2:
                            say("Stop DPS and wait for pod", True)
                        elif seconds_till_next_pod < stop_dps_call_timing + 5:
                            say("Push it")
                        debug("seconds_till_next_pod", seconds_till_next_pod, "get_hp_eta(shadow1_hp)", get_hp_eta(shadow1_hp))
                        game_state['shadow1_stop_dps_call'] = True

                if not game_state['shadow1_call'] and (game_state['shadow1_stop_dps_call'] and new_hp < shadow1_hp or get_hp_eta(shadow1_hp) < call_timing):
                    game_state['shadow1_call'] = True
                    say("Shadow out of time soon!", True)

                if new_hp <= shadow1_hp < game_state['lurker_hp']:
                    debug("Shadow1 HP reached")
                elif new_hp <= ps_fr_hps[0] < game_state['lurker_hp']:
                    debug("PS1 HP reached")
                elif new_hp <= ps_fr_hps[1] < game_state['lurker_hp']:
                    debug("PS2 HP reached")
                elif new_hp <= ps_fr_hps[2] < game_state['lurker_hp']:
                    debug("PS3 HP reached")
                elif new_hp <= ps_fr_hps[3] < game_state['lurker_hp']:
                    debug("FR HP reached")

            game_state['lurker_hp'] = new_hp
        
        elif stat_id == '1050':
            if value == '3':
                debug('Lurker became targetable')
                game_state['lurker_targetable'] = True
                if game_state['phase'] == 2:
                    start_p3()

            elif value == '5':
                debug('Lurker became untargetable')
                game_state['lurker_targetable'] = False

def event_character_died(character_id):
    if character_id in dynels:
        if is_player(character_id):
            game_state['players_died'] += 1
        if len(game_state['birds']) == 3 and dynels[character_id]['name'] == 'Eldritch Guardian' and game_state['early_ps'] and not game_state['early_ps_call']:
            game_state['early_ps_call'] = True
            say("Personal space will be early")
        if dynels[character_id]['name'] == 'Zero-Point Titan' and game_state['ps_counter'] < 4:
            game_state['hulk_spawned'] = False
            game_state['hulk_focus_warn'] = False
            if game_state['phase'] == 3:
                say("Hulk is dead")

def event_character_alive(character_id):
    if not game_state['start_time']:
        game_state['players_died'] = max(game_state['players_died'] - 1, 0)

def event_buff_added(character_id, buff_id, buff_name):
    if buff_name == 'Inevitable Doom':
        name = dynels[character_id]['name'] if character_id in dynels else 'an unknown person'

        if character_id not in dynels:
            error("Players doesn't seem to be registered! Re-enter the raid or type /reloadui in the chat")

        if not game_state['pod_targets']:
            game_state['last_pod_targeting'] = last_date

        game_state['pod_targets'].append(name)

        debug('Pod target found:', character_id, name)
        debug('Current targets:', game_state['pod_targets'])
        debug('Current game phase:', game_state['phase'])

    elif game_state['phase'] == 2 and buff_name == 'Whisper of Darkness':
        start_p3(-5)

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

    if get_lurker_id() == character_id:
        debug('Lurker command started:', command_name)

        if command_name == 'Pure Filth':
            if not game_state['last_filth']:
                game_state['start_time'] = last_date - timedelta(seconds=1)
                debug("Start time:", game_state['start_time'].isoformat())
            if game_state['needs_to_report_filth']:
                say("Filth is out")
                game_state['needs_to_report_filth'] = False
            game_state['last_filth'] = last_date
        elif command_name == 'Shadow Out Of Time':
            if game_state['phase'] == 1:
                game_state['phase'] = 2
            if game_state['phase'] == 3 or game_state['phase'] == 2 and len(game_state['birds']) == 3:
                say("Shadow out of time")
            game_state['last_shadow'] = last_date
        elif command_name.startswith('From Beneath'):
            say("Pod")
            game_state['last_pod'] = last_date
            game_state['pod_targets'] = []
        elif command_name == 'Personal Space' or command_name == 'Final Resort':
            pass

    if command_name == 'Downfall' and len(game_state['birds']) == 3:
        game_state['number_of_downfalls'] += 1
        debug('Downfall count:', str(game_state['number_of_downfalls']))
        if game_state['number_of_downfalls'] == 3:
            say("Kill it")
        else:
            say(str(game_state['number_of_downfalls']))

def event_ping():
    if game_state['pod_targets'] and (last_date - game_state['last_pod_targeting']).total_seconds() > 1:
        call_pod_targets()

def event_command_ended(character_id):
    if character_id not in dynels or not dynels[character_id]['command']:
        return

    (start_date, command_name) = dynels[character_id]['command']

    if get_lurker_id() == character_id:
        if command_name == 'Personal Space' or command_name == 'Final Resort':
            if game_state['ps_counter'] < 4 and ps_fr_hps[game_state['ps_counter']] > game_state['lurker_hp']:
                game_state['ps_counter'] += 1
    
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
    global last_real_date

    event = None
    params = None
    if line:
        m = log_line_pattern.match(line.strip())
        if not m:
            event_ping()
            return
    
        last_date = datetime.fromisoformat(m.group('date_string'))
        last_real_date = datetime.now()
        event = m.group('event_type')
        params = m.group('params').split('|')
    else:
        now = datetime.now()
        last_date += now - last_real_date
        last_real_date = now

    if event:
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

    event_ping()

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
                yield None
                continue
            yield line

def say(text, priority=False):
    print(last_date.isoformat(), "ANNOUNCEMENT", text)
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

    tts.Speak("Text-to-speech engine test.")
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
    debug("Agnitio NYR E10 caller bot v7 started")
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