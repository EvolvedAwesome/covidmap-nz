import pandas as pd
import requests
import urllib.request as urllib2
import numpy as np
import time
import googlemaps
import folium
import folium.plugins
import seaborn as sns
from datetime import date
from datetime import datetime
from branca.element import Template, MacroElement

LEGEND_TEMPLATE = f"""
{{% macro html(this, kwargs) %}}

<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>New Zealand Covid Map</title>
  <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/base/jquery-ui.css">

  <script src="https://code.jquery.com/jquery-1.12.4.js"></script>
  <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>

  <script>
  $( function() {{
    $( "#maplegend" ).draggable({{
                    start: function (event, ui) {{
                        $(this).css({{
                            right: "auto",
                            top: "auto",
                            bottom: "auto"
                        }});
                    }}
                }});
}});

  </script>

    <link rel="apple-touch-icon" sizes="57x57" href="/apple-icon-57x57.png">
    <link rel="apple-touch-icon" sizes="60x60" href="/apple-icon-60x60.png">
    <link rel="apple-touch-icon" sizes="72x72" href="/apple-icon-72x72.png">
    <link rel="apple-touch-icon" sizes="76x76" href="/apple-icon-76x76.png">
    <link rel="apple-touch-icon" sizes="114x114" href="/apple-icon-114x114.png">
    <link rel="apple-touch-icon" sizes="120x120" href="/apple-icon-120x120.png">
    <link rel="apple-touch-icon" sizes="144x144" href="/apple-icon-144x144.png">
    <link rel="apple-touch-icon" sizes="152x152" href="/apple-icon-152x152.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-icon-180x180.png">
    <link rel="icon" type="image/png" sizes="192x192"  href="/android-icon-192x192.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="manifest" href="/manifest.json">
    <meta name="msapplication-TileColor" content="#ffffff">
    <meta name="msapplication-TileImage" content="/ms-icon-144x144.png">
    <meta name="theme-color" content="#ffffff">

</head>
<body>


<div id='maplegend' class='maplegend'
    style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
     border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>

<div class='legend-title'>Legend <div>
<div class='legend-scale'>
  <ul class='legend-labels'>
    <li><span style='background:#f69630;opacity:0.7;'></span>Updated Today</li>
    <li><span style='background:#ff8e7f;opacity:0.7;'></span>Updated Multiple times</li>
    <li><span style='background:red;opacity:0.7;'></span>Updated less than 2 days ago</li>
    <li><span style='background:darkred;opacity:0.7;'></span>Updated more than 2 days ago</li>
    <li><i>Last updated: {str(datetime.now().strftime("%A %-d/%-m/%Y at %-I:%M %p"))}</i></li>
  </ul>
</div>
</div>

</body>
</html>

<style type='text/css'>
  .leaflet-bar a, .leaflet-bar a:hover {{
    background-color: rgb(0 0 0);
    color: #d9534f;
  }}
  .leaflet-bar a:hover {{
    background-color: #a94442;
  }}
  .maplegend .legend-title {{
    text-align: left;
    margin-bottom: 5px;
    font-weight: bold;
    font-size: 90%;
    }}
  .maplegend .legend-scale ul {{
    margin: 0;
    margin-bottom: 5px;
    padding: 0;
    float: left;
    list-style: none;
    }}
  .maplegend .legend-scale ul li {{
    font-size: 80%;
    list-style: none;
    margin-left: 0;
    line-height: 18px;
    margin-bottom: 2px;
    }}
  .maplegend ul.legend-labels li span {{
    display: block;
    float: left;
    height: 16px;
    width: 30px;
    margin-right: 5px;
    margin-left: 0;
    border: 1px solid #999;
    }}
  .maplegend .legend-source {{
    font-size: 80%;
    color: #777;
    clear: both;
    }}
  .maplegend a {{
    color: #777;
    }}
</style>
{{% endmacro %}}"""

def gen_palette(n):
    import seaborn as sns
    pal = sns.color_palette('Reds', 30)
    return pal.as_hex()

# Use a custom user agent to scrape the data from the health.govt.nz website
def get_data():
    url = 'https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-health-advice-public/contact-tracing-covid-19/covid-19-contact-tracing-locations-interest'

    opener = urllib2.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    response = opener.open(url)
    return pd.read_html(response.read())

def display_all_data(df):
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        print(df)

def data_to_geo(gmaps, df, col_name="Address"):
    #bus_mask = df[col_name].str.contains("Bus", regex=False, na=False)
    #print(gmaps.geocode(df.Address[0]))

    df["gcode"] = df.Address.apply(gmaps.geocode)

    display_all_data(df['gcode'])
    df["lat"] = [g[0]['geometry']['location']['lat'] if len(g) > 0 else None for g in df.gcode]
    df["long"] = [g[0]['geometry']['location']['lng'] if len(g) > 0 else None for g in df.gcode]

    return df

def download_static_map(df):
    # Check if the day of adding/updating is the same as today.
    def check_if_today(row):
        today = date.today()
        components = row['Date added'].split("-")
        return (int(today.strftime("%d")) == int(components[0]) and components[1] == today.strftime("%b"))

    # Calculate a range we will use to generate our zoom value
    range_avg = 0.5 * (df['lat'].max()-df['lat'].min()) + (df['long'].max()-df['long'].min())

    # For the theme that we are using
    tile_url = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    attri = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'

    # Add the map tiles and scale based on lat/long range and median of datapoints
    pointer_map = folium.Map(location=(df.lat.median(), df.long.median()), zoom_start=(10/275)*range_avg, tiles=None)
    folium.TileLayer(tile_url, name="Dark Theme", attr=attri, show=True, overlay=False).add_to(pointer_map)
    # Theres a bug that means multiple layers don't display right
    #folium.TileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png', name="Light Theme", attr=attri).add_to(pointer_map)

    # Add custom code/headers/favicon/title etc
    macro = MacroElement()
    macro._template = Template(LEGEND_TEMPLATE)

    pointer_map.get_root().add_child(macro)

    #folium.plugins.LocateControl(auto_start=False, flyTo=True).add_to(pointer_map)

    f_pointer_map = folium.FeatureGroup(name='Locations of Interest').add_to(pointer_map)
    f_pointer_today_map = folium.FeatureGroup(name='Locations of Interest Updated Today').add_to(pointer_map)
    f_heat_map = folium.FeatureGroup(name='Viral Heat Map', show=False).add_to(pointer_map)
    f_circ_map = folium.FeatureGroup(name='Circle Indicator Map', show=False).add_to(pointer_map)
    folium.LayerControl().add_to(pointer_map)

    # Data: (e.g.)
    # Location name                                          Denny's CBD
    #Address                        51 Hobson Street Auckland CBD, 1010
    #Day                                               Friday 13 August
    #Times                                            1.00 am - 1.30 am
    # Colour by date added
    palette = gen_palette(100)

    # For all our simulations we will use the data without
    # bus routes.
    bus_mask = df.Address.str.contains("Bus")
    df_bus_routes = df[bus_mask]
    df = df[~bus_mask]

    # Heatmap
    folium.plugins.HeatMap(list(zip(df.lat.values, df.long.values)), show=False).add_to(f_heat_map)
    
    #df_new = df.groupby('Day').apply(list).reset_index(name='Index')
    #print(df)
    #folium.plugins.HeatMapWithTime((df.lat, df.long), show=False).add_to(f_heat_map)

    # We calculate where there are duplicates
    # Marks all duplicates as true
    duplicates_mask = df.duplicated('Location name', keep=False)
    df_dupl = df[duplicates_mask]
    df_nodupl = df[~duplicates_mask]

    # Handle duplicates
    last_dpl = None
    last_dpl_data = None
    current_html_str = ""
    df_dupl = df_dupl.sort_values('Location name')
    for index, row in df_dupl.iterrows():
        if last_dpl == None or last_dpl != row["Location name"]:
            # End previous sequence
            if last_dpl != None:
                # Ending html
                current_html_str += """</div>
  <a class="carousel-control-prev" href="#carouselExampleControls" role="button" data-slide="prev">
    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
    <span class="sr-only">Previous</span>
  </a>
  <a class="carousel-control-next" href="#carouselExampleControls" role="button" data-slide="next">
    <span class="carousel-control-next-icon" aria-hidden="true"></span>
    <span class="sr-only">Next</span>
  </a>
</div>"""
                data_hover = f"<i>{last_dpl}</i>"
                # Push marker
                folium.Marker(location=(last_dpl_data['lat'],last_dpl_data['long']), tooltip=data_hover, popup=current_html_str, icon=folium.Icon(color="lightred", icon="exclamation-triangle", prefix='fa')).add_to(f_pointer_map)
                # Clear string
                current_html_str = ""
            last_dpl = row["Location name"]
            last_dpl_data = row
            # We start the sequence
            # Starting html
            current_html_str += f"""<div id="carouselExampleControls" class="carousel slide" data-ride="carousel">
  <div class="carousel-inner">
    <div class="carousel-item active">
        <table><thead><tr><th>{row['Location name']}</th></tr></thead><tbody><tr><td>{row['Day']}</td></tr><tr><td>{row['Times']}</td></tr><tr><td><a href='https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-health-advice-public/contact-tracing-covid-19/covid-19-contact-tracing-locations-interest'>More information</a></td></tr></tbody></table>
    </div>"""
        elif last_dpl == row["Location name"]:
            # We still on the same item
            # Iterate HTML
            current_html_str += f"""<div class="carousel-item">
        <table><thead><tr><th>{row['Location name']}</th></tr></thead><tbody><tr><td>{row['Day']}</td></tr><tr><td>{row['Times']}</td></tr><tr><td><a href='https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-health-advice-public/contact-tracing-covid-19/covid-19-contact-tracing-locations-interest'>More information</a></td></tr></tbody></table>
            </div>"""

    # Handle non-duplicates
    for index, row in df_nodupl.iterrows():
        today = date.today()

        # We colour markers older than 2 days a dark red.
        marker_col = "red"
        if int(today.strftime("%d")) - int(row['Date added'].split("-")[0]) > 2 and row['Date added'].split("-")[1] == today.strftime("%b"):
            marker_col = "darkred"

        data_hover = f"<i>{row['Location name']}</i>"
        data_popup = f"<table><thead><tr><th>{row['Location name']}</th></tr></thead><tbody><tr><td>{row['Day']}</td></tr><tr><td>{row['Times']}</td></tr><tr><td><a href='https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-health-advice-public/contact-tracing-covid-19/covid-19-contact-tracing-locations-interest'>More information</a></td></tr></tbody></table>"

        # Add markers
        if not check_if_today(row):
            folium.Marker(location=(row['lat'],row['long']), tooltip=data_hover, popup=data_popup, icon=folium.Icon(color=marker_col, icon="exclamation-triangle", prefix='fa')).add_to(f_pointer_map)
        else:
            folium.Marker(location=(row['lat'],row['long']), tooltip=data_hover, popup=data_popup, icon=folium.Icon(color='orange', icon="exclamation-triangle", prefix='fa')).add_to(f_pointer_today_map)

        #folium.Marker(location=(row['lat'],row['long']), popup=f"<p>{row['Location name']}", icon=folium.plugins.BeautifyIcon(background_color=bgc, icon="exclamation-triangle", icon_shape="marker",  prefix='fa', borderColor=bgc)).add_to(f_pointer_map)

        # Circle Markers
        folium.CircleMarker(radius=15, location=(row['lat'],row['long']), popup=data_popup, tooltip=data_hover, color="red", stroke=False, fill=True, fill_color="red", show=False).add_to(f_circ_map)

        pointer_map.save("public/index.html")
    #<br />{row['Address']}<br />{row['Day']}<br />{row['Times']}</p>"

DATA_SCRAPE = True
MAP_GEN = True
if __name__ == "__main__":
    if DATA_SCRAPE:
        # Scrape data
        print("Collecting data from MOH website")
        dfs = get_data()

        print("Parsing data")
        # Convert data into usage format
        # We do this shuffle as there are some weird characters in the date_added col
        # For just the coromandel locations. Could be related to use of latin characters
        # in the names
        dfs[-2]['Date added'] = dfs[-2]['Date added']
        dfs[-2].drop('Date added', axis=1, inplace=True)
        df = pd.concat(dfs[:-1])
        print(df)

        print("Comparing to current data")
        df_old = pd.read_csv("data.csv", index_col=0)
        df_old.drop(columns=['gcode', 'lat', 'long'], axis=1, inplace=True)

        df_diff = pd.concat([df,df_old]).drop_duplicates(keep=False)
        print(df_diff)
        if len(df_diff) > 0:
            print("Updating to match changes at source of truth")
            gmaps = googlemaps.Client(key="")
            df = data_to_geo(gmaps, df)

            print("Writing new dataset to CSV")
            df.to_csv("data.csv")

    if MAP_GEN:
        print("Importing dataset from CSV")
        df = pd.read_csv("data.csv", index_col=0)
        print("Generating map html files")
        download_static_map(df)
