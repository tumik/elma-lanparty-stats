from flask import Flask, request, render_template, redirect, url_for, flash
import os
from datetime import datetime
import pathlib
from elma import State
from elma.utils import format_time
from werkzeug.utils import secure_filename
import shutil
import re

app = Flask(__name__)
app.secret_key = 'elma-stats-combine-secret-key'
UPLOAD_FOLDER = 'uploads'
STATE_STORE_FOLDER = 'state_store'
ALLOWED_EXTENSIONS = {'dat'}

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATE_STORE_FOLDER, exist_ok=True)
os.makedirs('static', exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function for converting time in hundredths to a formatted string
def format_total_time(time_in_hundredths):
    # Custom formatting for the Finnish version (mm:ss:ms)
    minutes, remainder = divmod(time_in_hundredths, 6000)
    seconds, hundredths = divmod(remainder, 100)
    return f"{minutes:02d}:{seconds:02d}:{hundredths:02d}"

# Create custom Finnish version of stats.txt
def create_finnish_stats_txt(state):
    top10s = ''
    # Single player only
    top10s += f'\n\nYksinpelitulokset:\n'
    for i in range(18):  # Only levels 1-18
        level_times = []
        original_times = []
        
        # Get the slowest time for this level from the combined statistics (to use as penalty)
        slowest_time = None
        
        # Check all single player times across all players
        for time in state.times[i].single:
            if time.time > 0 and (slowest_time is None or time.time > slowest_time):
                slowest_time = time.time
        
        # Always use the slowest time from combined statistics as penalty
        # Only fall back to 10 minutes if absolutely no times exist
        penalty = slowest_time if slowest_time is not None else 60000
        
        for time in state.times[i].single:
            # Check if this kuski's result is already in the list
            if not any(t.kuski == time.kuski for t in original_times):
                original_times.append(time)
                # Check if this is a penalty time (no valid time)
                is_penalty = False
                player_time = time.time
                
                # If time is invalid, use penalty
                if player_time <= 0:
                    player_time = penalty
                    is_penalty = True
                    
                level_times.append((player_time, time.kuski, is_penalty))
        
        if not level_times:
            int_name = f"{i+1}, {get_finnish_level_name(i)}"
            top10s += f'\nKenttä {int_name}:\n'
            continue
            
        # Sort times
        level_times.sort()
        
        # Format the level header
        int_name = f"{i+1}, {get_finnish_level_name(i)}"
        top10s += f'\nKenttä {int_name}:\n'
        
        # Format the times
        for time, kuski, is_penalty in level_times:
            time_str = format_total_time(time)
            penalty_marker = " (P)" if is_penalty else ""
            top10s += f'    {time_str}    {kuski}{penalty_marker}\n'
    
    # Format the full stats text in Finnish
    stats_text = f'{top10s}'
    
    return stats_text

# Function to get detailed level-by-level information for a player
def get_player_level_details(state, player_name):
    """
    Get detailed information about the player's times for each level.
    
    Args:
        state: State object
        player_name: name of the player or None for combined best result
        
    Returns:
        List of dictionaries with level details including times, penalties, etc.
    """
    level_details = []
    total_time = 0
    
    # Only consider levels 1-18
    for i in range(18):
        # Get the slowest time for this level from the combined statistics (to use as penalty)
        slowest_time = None
        
        # Check all single player times across all players
        for time in state.times[i].single:
            if time.time > 0 and (slowest_time is None or time.time > slowest_time):
                slowest_time = time.time
        
        # Always use the slowest time from combined statistics as penalty
        # Only fall back to 10 minutes if absolutely no times exist
        penalty = slowest_time if slowest_time is not None else 60000
        
        # Get best time for this level based on player_name
        if player_name is not None:
            # Get player's best single player time for this level
            best_time = None
            for time in state.times[i].single:
                if time.kuski == player_name and time.time > 0:
                    if best_time is None or time.time < best_time:
                        best_time = time.time
        else:
            # For combined best result, find the best time from any player
            best_time = None
            for time in state.times[i].single:
                if time.time > 0:
                    if best_time is None or time.time < best_time:
                        best_time = time.time
        
        time_type = "single"
        is_penalty = False
        
        # Apply penalty if no valid time
        if best_time is None:
            best_time = penalty
            time_type = "penalty"
            is_penalty = True
            
        # Add time to total
        total_time += best_time
        
        # Format the time as a string
        time_str = format_total_time(best_time)
        
        # Create level detail entry
        level_detail = {
            'level_number': i + 1,
            'level_name': get_finnish_level_name(i),
            'time': best_time,
            'time_str': time_str,
            'type': time_type,
            'is_penalty': is_penalty,
            'penalty_value': penalty if is_penalty else 0,
            'penalty_str': format_total_time(penalty) if is_penalty else None
        }
        
        level_details.append(level_detail)
    
    return level_details, total_time

# Finnish level names lookup
def get_finnish_level_name(level_index):
    # Mapping of English level names to Finnish
    level_names = [
        "Lämmittely", "Tasainen rata", "Kaksoishuiput", "Yli ja ali", 
        "Ylämäkitaistelu", "Pitkä matka", "Korkealle lentäjä", "Hippa",
        "Tunneli kauhu", "Tasangot", "Painovoimakyyti", "Taivasaaret",
        "Kukkulalegenda", "Kierros", "Käärmeen tarina", "Uusi aalto",
        "Labyrintti", "Spiraali", "Käännös", "Ylösalaisin",
        "Hirttäjäinen", "Pujottelu", "Sieni", "Hullujenhuone",
        "Auringonnousu", "Kylmä yö", "Liukutukit", "Liian kuuma",
        "Miinakenttä", "Hedelmäpeli", "Matokuulat", "Sateenkaari",
        "Jäälautta", "Edge hog", "AMG", "Bada Bing!",
        "Härkä laukalla", "Hankala matsi", "Australian Grand Prix", "The Steppes of Narud",
        "Velociraptor", "Samba!", "Geneva", "Spaghetti",
        "Heureka", "Adios amigo", "Velociraptor 2", "Banana Split",
        "X-mas", "DC Metro", "Et tu, Brute?", "The Beach",
        "Castle Hill", "Swiss Knife", "Batak 2", "Pigland"
    ]
    
    if 0 <= level_index < len(level_names):
        return level_names[level_index]
    return f"Kenttä {level_index+1}"

# Modified total_time function that only considers levels 1-18
def custom_total_time(state, player=None):
    """
    Calculate total time for levels 1-18 only.
    
    Args:
        state: State object
        player: name of the player, or None for anonymous total time
        
    Returns:
        Tuple of (total time in hundredths of a second, boolean indicating if penalty was applied, 
        boolean indicating if all times are penalties)
    """
    tt = 0
    has_penalty = False
    all_penalties = True  # Track if all times are penalties
    
    # Only consider levels 1-18
    for i in range(18):
        # Get the slowest time for this level from the combined statistics (to use as penalty)
        slowest_time = None
        
        # Check all single player times across all players
        for time in state.times[i].single:
            if time.time > 0 and (slowest_time is None or time.time > slowest_time):
                slowest_time = time.time
        
        # Always use the slowest time from combined statistics as penalty
        # Only fall back to 10 minutes if absolutely no times exist
        penalty = slowest_time if slowest_time is not None else 60000
        
        # Get player's best time for this level (single player only)
        if player is not None:
            pr = None
            for time in state.times[i].single:
                if time.kuski == player and time.time > 0:
                    if pr is None or time.time < pr:
                        pr = time.time
        else:
            # For combined best result, find the best time from any player
            pr = None
            for time in state.times[i].single:
                if time.time > 0:
                    if pr is None or time.time < pr:
                        pr = time.time
        
        # Apply penalty if the player has no time
        if pr is None:
            pr = penalty
            has_penalty = True
        else:
            # If we found at least one valid time, not all are penalties
            all_penalties = False

        tt += pr
    return (tt, has_penalty, all_penalties)

@app.route('/', methods=['GET', 'POST'])
def index():
    # Handle file upload if POST request
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('Tiedosto-osa puuttuu')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if user does not select a file, browser might submit an empty file
        if file.filename == '':
            flash('Ei valittua tiedostoa')
            return redirect(request.url)
            
        # Check if the file name is STATE.DAT (case-insensitive)
        if file.filename.upper() != "STATE.DAT":
            flash(f'Tiedoston nimen täytyy olla STATE.DAT (kirjainkoolla ei ole väliä), mutta annoit tiedoston "{file.filename.upper()}"')
            #return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Process the file with elma library
            try:
                state = State.load(file_path)
                
                # Get player name and total time
                player_name = state.player_A_name
                total_time = state.total_time(player_name)
                
                # Create unique filename with player name, total time and timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                filename_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                store_filename = f"{player_name}_{total_time}_{filename_timestamp}.dat"
                store_path = os.path.join(STATE_STORE_FOLDER, secure_filename(store_filename))
                
                # Copy the file to the state store
                shutil.copy2(file_path, store_path)
                
                flash(f'STATE.DAT käsitelty onnistuneesti pelaajalle {player_name}')
                return redirect(url_for('index'))
                
            except Exception as e:
                flash(f'Virhe tiedoston käsittelyssä: {str(e)}')
                return redirect(request.url)
        else:
            flash('Virheellinen tiedosto. Varmista, että tiedosto on .dat-muotoinen ja että se on nimetty oikein.')
    
    # Load stats for both GET and POST (after redirect) requests
    combined_state = State()
    
    # PHASE 1: First process all files to build the combined state
    combined_state = State()
    
    # Käytetään apurakennetta seuraamaan pelaajien parhaita aikoja
    best_times = {}  # Rakenne: { level_index: { player_name: best_time } }
    
    # Alusta tietorakenne
    for i in range(18):  # Vain tasot 1-18 
        best_times[i] = {}
    
    # Ensin käy läpi kaikki tiedostot ja löydä kunkin pelaajan paras aika joka kentälle
    for filename in os.listdir(STATE_STORE_FOLDER):
        if filename.endswith('.dat'):
            file_path = os.path.join(STATE_STORE_FOLDER, filename)
            try:
                state = State.load(file_path)
                
                # Käy läpi jokaisen tason ajat
                for i, top10 in enumerate(state.times):
                    if i >= 18:  # Käsitellään vain tasot 1-18
                        continue
                        
                    # Käy läpi single-player ajat
                    for time in top10.single:
                        if time.kuski and time.time > 0:
                            # Tarkista onko tämä paras aika tälle pelaajalle tällä kentällä
                            if (time.kuski not in best_times[i] or 
                                time.time < best_times[i][time.kuski]):
                                best_times[i][time.kuski] = time.time
                
                # Kerää pelaajat yhdistettyyn tilaan
                for player in state.players:
                    if player.name:  # Skip empty player names
                        # Check if player already exists in combined_state
                        player_exists = False
                        for existing_player in combined_state.players:
                            if existing_player.name == player.name:
                                player_exists = True
                                break
                        
                        # If player doesn't exist, add to combined state
                        if not player_exists:
                            combined_state.players.append(player)
                            combined_state.player_count += 1
                            
            except Exception as e:
                print(f"Virhe tiedoston {filename} käsittelyssä: {str(e)}")
    
    # PHASE 2: Nyt rakenna combined_state käyttäen aiemmin löydettyjä parhaita aikoja
    from elma.models import Top10Time
    
    # Lisää parhaat ajat combined_state-objektiin
    for level_idx, players_times in best_times.items():
        for player_name, best_time in players_times.items():
            time_entry = Top10Time(best_time, player_name)
            combined_state.times[level_idx].single.append(time_entry)
    
    # Sort times for each level in the combined state
    for top10 in combined_state.times:
        top10.single.sort(key=lambda x: x.time if x.time > 0 else float('inf'))
        top10.multi.sort(key=lambda x: x.time if x.time > 0 else float('inf'))
        
        # No longer limiting to top 10 times
        # Keep all valid times
    
    # PHASE 2: Now process player data from the fully built combined_state
    players_data = []
    processed_players = set()  # Keep track of processed players to avoid duplicates
    
    # Add player data from combined state
    for player in combined_state.players:
        if player.name and player.name not in processed_players:
            # Use combined_state for player times
            total_time, has_penalty, all_penalties = custom_total_time(combined_state, player.name)
            
            # Get detailed level-by-level information
            level_details, calculated_total = get_player_level_details(combined_state, player.name)
            
            # Only include players with at least one valid time
            if not all_penalties:
                players_data.append({
                    'name': player.name,
                    'total_time': total_time,
                    'has_penalty': has_penalty,
                    'level_details': level_details
                })
                processed_players.add(player.name)
    
    # Etsi pelaajat myös ajoista (jotka eivät välttämättä ole players-listalla)
    # Käy läpi kaikki ajat ja tunnista niissä esiintyvät pelaajat
    for i in range(18):  # Vain kentät 1-18
        for time in combined_state.times[i].single:
            if time.kuski and time.kuski not in processed_players:
                # Tämä pelaaja on ajoissa mutta ei players-listalla
                total_time, has_penalty, all_penalties = custom_total_time(combined_state, time.kuski)
                level_details, calculated_total = get_player_level_details(combined_state, time.kuski)
                
                # Only include players with at least one valid time
                if not all_penalties:
                    players_data.append({
                        'name': time.kuski,
                        'total_time': total_time,
                        'has_penalty': has_penalty,
                        'level_details': level_details
                    })
                    processed_players.add(time.kuski)
    
    # Sort players by total time
    players_data.sort(key=lambda x: x['total_time'])
    
    # Calculate "Yhdistetty paras tulos" (combined best result) 
    combined_best_time, combined_has_penalty, _ = custom_total_time(combined_state, None) if combined_state else (0, False, True)
    
    # Get detailed level-by-level information for combined best result
    combined_level_details = []
    if combined_state:
        combined_level_details, _ = get_player_level_details(combined_state, None)
    
    # Add "Yhdistetty paras tulos" as the first entry in the player list
    players_data.insert(0, {
        'name': 'Yhdistetty paras tulos',
        'total_time': combined_best_time,
        'has_penalty': combined_has_penalty,
        'level_details': combined_level_details
    })
    
    # Generate custom Finnish stats
    stats_text = create_finnish_stats_txt(combined_state) if combined_state else "Ei dataa saatavilla"
    
    return render_template('index.html', stats_text=stats_text, players=players_data, format_total_time=format_total_time)

# Copy logo to static directory if it exists in templates
logo_source = os.path.join('templates', 'retro.jpg')
logo_dest = os.path.join('static', 'retro.jpg')
if os.path.exists(logo_source) and not os.path.exists(logo_dest):
    shutil.copy2(logo_source, logo_dest)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
