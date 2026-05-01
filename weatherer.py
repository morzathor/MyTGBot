import requests as rq
from datetime import datetime
from datetime import datetime as _dt

###### Constants ######
BASE_URL = f'https://api.open-meteo.com/v1/forecast'
DEFAULT_PARAMETERS = {
          'latitude':'35.8327',
          'longitude':'50.9915',
          'daily':'temperature_2m_max,temperature_2m_min',
          'hourly':'temperature_2m,showers,rain',
          'current':'temperature_2m',
          'timezone':'Asia/Seoul',
          'forecast_days':1}

###### Main function ######
def get_timezone_from_coordinates(latitude, longitude):
    """Get timezone name from latitude and longitude coordinates."""
    try:
        url = 'https://api.open-meteo.com/v1/timezone'
        resp = rq.get(url, params={'latitude': latitude, 'longitude': longitude}, timeout=5)
        data = resp.json()
        tz = data.get('timezone')
        if tz:
            return tz
        # fallback to abbreviation/offset if available
        abbr = data.get('abbreviation') or data.get('timezone_abbreviation')
        if abbr:
            return abbr
        return 'UTC'
    except (rq.exceptions.ConnectionError, rq.exceptions.Timeout, Exception):
        return 'UTC'

def main():
    while True:
        print("\nWelcome to weather forecasting app!!")
        choice = int(input("""
                        1.Show current forecast
                        2.Show daily forecast
                        3.Show hourly forecast
                        4.Set location (Given location will be valid until next start)
                        5.Exit
                        Choose what to do: """))

        if choice == 1:
            current_forecast()
            input("\nPress enter to continue...\n")
            continue
        elif choice == 2:
            user_input = int(input("Enter forecast days: "))
            if user_input >=16:
                print("\n ***** Limit is 16! *****")
                input("\nPress enter to continue...\n")
                continue
              
            print(daily_forecast(user_input))
            input("\nPress enter to continue...\n")
            continue
        elif choice == 3:
            user_input = int(input("Enter forecast days: "))
            if user_input >=16:
                print("\n ***** Limit is 16! *****")
                input("\nPress enter to continue...\n")
                continue
            h_data = hourly_forecast(user_input)
            for i in h_data:
                print(i)
            input("\nPress enter to continue...\n")
            continue
        
        elif choice == 4:
            ###### Change parameters based on user's location ######
            city_input = str(input("Enter your city: "))
            print(type(city_input))
            longi_tude = get_reverse_location(city_input)[0][0]
            lati_tude = get_reverse_location(city_input)[0][1]
            DEFAULT_PARAMETERS['longitude']= str(longi_tude)
            DEFAULT_PARAMETERS['latitude']= str(lati_tude)
            continue
        elif choice == 5:
            break
###### Retrieve and show hourly forecast ######
def hourly_forecast(user_hours):
    try:
        DEFAULT_PARAMETERS['forecast_days'] =  user_hours

        the_req = rq.get(BASE_URL, params=DEFAULT_PARAMETERS, timeout=10)
        the_response = the_req.json()
        timestamps = the_response['hourly']['time']
        fix_date = [datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M") for ts in timestamps]
        hourl = []
        count_one = 0
        for i in fix_date:
            hourl.append(f"{i}: and the temp is: {the_response['hourly']['temperature_2m'][count_one]}")
            count_one += 1
        return hourl
    except (rq.exceptions.ConnectionError, rq.exceptions.Timeout):
        return ["❌ Weather service is currently unavailable. Please try again later."]
    except Exception as e:
        return [f"❌ Error fetching weather data: {str(e)}. Please try again."]


###### Retrieve and show daily forecast ######
def daily_forecast(user_days):
    try:
        DEFAULT_PARAMETERS['forecast_days'] = user_days

        the_req = rq.get(BASE_URL, params=DEFAULT_PARAMETERS, timeout=10)
        the_response = the_req.json()

        timestamps = the_response['daily']['time']
        fix_date = [datetime.fromisoformat(ts).strftime("%Y-%m-%d") for ts in timestamps]
        e = 0
        daily = []
        for i in fix_date:
            daily.append(f"{i}: maximum: {the_response['daily']['temperature_2m_max'][e]} -- minimum: {the_response['daily']['temperature_2m_min'][e]}")
            e += 1
        return daily
    except (rq.exceptions.ConnectionError, rq.exceptions.Timeout):
        return ["❌ Weather service is currently unavailable. Please try again later."]
    except Exception as e:
        return [f"❌ Error fetching weather data: {str(e)}. Please try again."]

###### Retrieve and show current forecast ######
def current_forecast():
    try:
        # Fetch hourly data and pick the hour nearest to user's local time
        the_req = rq.get(BASE_URL, params=DEFAULT_PARAMETERS, timeout=10)
        the_response = the_req.json()
    except (rq.exceptions.ConnectionError, rq.exceptions.Timeout):
        return "❌ Weather service is currently unavailable. Please try again later."
    except Exception as e:
        return f"❌ Error fetching weather data: {str(e)}. Please try again."

    # Prefer hourly series
    hours = the_response.get('hourly', {})
    times = hours.get('time', [])
    temps = hours.get('temperature_2m', [])

    try:
        if not times or not temps:
            cur = the_response.get('current', {})
            timestamps = cur.get('time')
            if timestamps:
                fix_date = datetime.fromisoformat(timestamps).strftime("%Y-%m-%d %H:%M")
                return f"{fix_date}: current temp: {cur.get('temperature_2m')}"
            return "No data available"
    except Exception as e:
        return f"❌ Error processing weather data: {str(e)}"

    try:
        tz_name = DEFAULT_PARAMETERS.get('timezone')
        from datetime import timezone, timedelta
        try:
            from zoneinfo import ZoneInfo
            if tz_name and '/' in tz_name:
                tzinfo = ZoneInfo(tz_name)
            else:
                raise Exception("Not IANA")
        except Exception:
            # Parse GMT offset like 'GMT+3:30' or 'UTC+02:00'
            tzinfo = timezone.utc
            if isinstance(tz_name, str):
                import re
                m = re.match(r'^(?:GMT|UTC)?([+-])(\d{1,2})(?::?(\d{2}))?$', tz_name)
                if m:
                    sign = 1 if m.group(1) == '+' else -1
                    hours_off = int(m.group(2))
                    mins_off = int(m.group(3) or 0)
                    offset = sign * (hours_off * 3600 + mins_off * 60)
                    tzinfo = timezone(timedelta(seconds=offset))


        now_utc = datetime.utcnow().replace(tzinfo=timezone.utc)
        local_now = now_utc.astimezone(tzinfo)
        minute = local_now.minute
        if minute >= 30:
            local_target = (local_now.replace(second=0, microsecond=0) + timedelta(hours=1)).replace(minute=0)
        else:
            local_target = local_now.replace(minute=0, second=0, microsecond=0)


        target_naive = local_target.replace(tzinfo=None)

        # find closest timestamp index
        best_idx = None
        best_diff = None
        for i, ts in enumerate(times):
            try:
                t = _dt.fromisoformat(ts)
            except Exception:
                continue
            diff = abs((t - target_naive).total_seconds())
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best_idx = i

        if best_idx is None:
            return "No hourly data available"

        chosen_time = _dt.fromisoformat(times[best_idx]).strftime("%Y-%m-%d %H:%M")
        chosen_temp = temps[best_idx] if best_idx < len(temps) else None
        return f"{chosen_time}: current temp: {chosen_temp}"
    except Exception as e:
        return f"❌ Error processing current forecast: {str(e)}"

def get_reverse_location(city):
    
    try:
        resp = rq.get(url=f"https://geocode.maps.co/search?q={city}&api_key=693ccfe2e6dbb326177708oxe9fc23e", timeout=10)
        data = resp.json()
    except ValueError:
        return []
    except (rq.exceptions.ConnectionError, rq.exceptions.Timeout):
        return []
    except Exception:
        return []
    # Return a list of candidate dicts 
    results = []
    for item in data:
        # include all results
        address = item.get("address") or {}
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        try:
            lon_f = float(lon)
            lat_f = float(lat)
        except (TypeError, ValueError):
            continue

        # determine IANA timezone for this candidate
        try:
            tz_url = 'https://api.open-meteo.com/v1/timezone'
            tz_resp = rq.get(tz_url, params={'latitude': lat_f, 'longitude': lon_f}, timeout=5)
            tz_data = tz_resp.json()
            timezone = tz_data.get('timezone') or tz_data.get('abbreviation') or tz_data.get('timezone_abbreviation') or 'UTC'
        except Exception:
            timezone = 'UTC'


        state = address.get("state") or address.get("county") or address.get("region") or address.get("district") or ''
        country_code = (address.get("country_code") or '').upper()

        results.append({
            'lon': lon_f,
            'lat': lat_f,
            'timezone': timezone,
            'state': state,
            'country_code': country_code,
            'display_name': item.get('display_name', ''),
            'addresstype': item.get('addresstype')
        })

    return results

if __name__ == "__main__":
    main()


