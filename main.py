from machine import Pin
import network
import socket
from time import sleep
import random
import utime
import urequests
import dht
import math

try:
    import usocket as socket
except:
    import socket

import esp
esp.osdebug(None)

import gc
gc.collect()

import routines
import wifi_config
import json

ssid = config.SSID
password = wifi_config.PASSWORD

led = Pin(2,Pin.OUT)
sensor = dht.DHT11(Pin(14))

stoveState = 'off'
mode = 'off'
temperature = "70"
humidity = "50"
lowTemp = "70"
highTemp = "72"
startup = False
testMode = False


onHost = "https://trigger.esp8266-server.de/api/?id=5179&hash=b08808f8604d98ff07e51567f2422f08";
offHost= "https://trigger.esp8266-server.de/api/?id=5180&hash=b08808f8604d98ff07e51567f2422f08";


def read_sensor():
  try:
    sensor.measure()
    temp = sensor.temperature()
    # uncomment for Fahrenheit
    temp = temp * (9/5) + 32.0
    hum = sensor.humidity()
    print('Temperature: ' + str(round(temp,2)))
    print('Humidity: ' + str(round(hum,2)))
    if (isinstance(temp, float) or isinstance(temp, int)) and (isinstance(hum, int) or isinstance(hum, float)):
      temp = round(temp,2)
      hum = round(hum,2)
      return temp, hum
    else:
      temp = -100
      hum = -100
      return temp,hum
  except OSError as e:
    temp = -100
    hum = -100
    return temp,hum


def sendWebPage():
    response = routines.get_html('pellet_stove_version1.html')
    if response != "":
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(response)
        conn.close()
    else:
        print('Web Page Not Found')

def sendData():
    global stoveState, startup
    if mode == "auto":        
        if float(temperature) <= float(lowTemp):
            turnStoveOn()
        if float(temperature) >= float(highTemp):
            if stoveState == 'on':
                try:
                    response = urequests.get(offHost)
                    if response.status_code == 200:
                        print('Get Request successfull')
                    else:
                        print(f"Get Request failed with status code: {response.status_code}")
                except Exception as e:
                    print(f"An error occurred: {e}")
                finally:
                    if 'response' in locals() and response:
                        response.close()
                stoveState = 'off'
                led.off()
    if startup == True:
        #get mode, stoveState, lowTemp, highTemp from file at startup
        if routines.fileExist('config.json'):
            getDataFromFile()
        else:
            saveDataToFile()
        startup = False
    data = {'temp': temperature, 'humid': humidity, "mode": mode, 'stoveState': stoveState, 'lowTemp': lowTemp, 'highTemp': highTemp}
    response = json.dumps(data)
    #print('Data in sendTemps = ', response)
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: application\json\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()
    
def sendMode():
    data = {'mode': mode, 'stoveState': stoveState}
    response = json.dumps(data)
    print('Data in sendModes = ', response)
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: application\json\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response)
    conn.close()
    
def turnStoveOn():
    global stoveState
    if testMode == False:
        if stoveState != 'on':
            try:
                response = urequests.get(onHost)
                if response.status_code == 200:
                    stoveState = 'on'
                    led.on()
                    print('Get Request successfull')
                else:
                    print(f"Get Request failed with status code: {response.status_code}")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                if 'response' in locals() and response:
                    response.close()
    else:
        stoveState = 'on'
        led.on()
def turnStoveOff():
    global stoveState
    if testMode == False:
        if stoveState != 'off':
            try:
                response = urequests.get(offHost)
                if response.status_code == 200:
                    stoveState = 'off'
                    led.off()
                    print('Get Request successfull')
                else:
                    print(f"Get Request failed with status code: {response.status_code}")
            except Exception as e:
                print(f"An error occurred: {e}")
            finally:
                if 'response' in locals() and response:
                    response.close()
    else:
        stoveState = 'off'
        led.off()
    
def qs_parse(qs):
    parameters = {}
    if not qs:
        return parameters
    ampersandSplit = qs.split("&")
    print("& split : ", ampersandSplit)
    for element in ampersandSplit:
        equalSplit = element.split(":")
        if len(equalSplit) == 2:
            parameters[equalSplit[0]] = equalSplit[1]
    return parameters

def saveDataToFile():
    data = {
        "mode": mode,
        "stoveState": stoveState,
        "lowTemp": lowTemp,
        "highTemp": highTemp
    }
    try:
        with open("config.json", "w") as f:
            json.dump(data,f)
        print("JSON data successfully written to config.json")
    except OSError as e:
        print("Error writing JSON data:", e)
        
def getDataFromFile():
    global mode,stoveState,lowTemp,highTemp
    try:
        with open("config.json", "r") as f:
            data = json.load(f)
        print("JSON data loaded successfully", data)
        mode = data['mode']
        stoveState = data['stoveState']
        lowTemp = data['lowTemp']
        highTemp = data['highTemp']
        print(f"From File: mode:{mode}, stoveState:{stoveState}, lowTemp:{lowTemp}, highTemp{highTemp}")
    except OSError as e:
        print("Error reading JSON file:", e)
    except ValueError as e:
        print("Error parsing JSON data:", e) 


#connect to wifi
routines.connect_to_wifi(ssid,password)
startup = True

#start sockets
addr = socket.getaddrinfo('192.168.1.159', 80)[0][-1]
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((addr))
s.listen(5)

print('Listening on', addr)
readDelay = 5000

start = utime.ticks_us()


while True:
    if utime.ticks_us() - start > readDelay:
        #print("get temperature and humidity")
        temp, hum = read_sensor()
        if temp != -100:
            temperature = temp
        if hum != -100:
            humidity = hum
        #temperature = readTemperature()
        #humidity = readHumidity()
        start = utime.ticks_us()
    try:
        if gc.mem_free() < 102000:
            gc.collect()
        conn, addr = s.accept()
        conn.settimeout(3.0)
        #print('Got a connection from %s' % str(addr))
        request = conn.recv(1024)
        conn.settimeout(None)
        request = str(request)

        #print('Content = %s' %request)
        mode_on = request.find('/mode=on')
        mode_off = request.find('/mode=off')
        mode_auto = request.find('/mode=auto')
        getData = request.find('/data')
        saveSetting = request.find('/settings')
        syncOn = request.find('/syncOn')
        syncOff = request.find('/syncOff')
        #-----------------------------------------------------------------------------------
        # check if user made changes to low and high temperature settings
        #-----------------------------------------------------------------------------------
        url = request.split()[1]
        if '?' in url:
            path,query_string = url.split('?',1)
            print("URL requested:", url)
            params = qs_parse(query_string)
            # Print the extracted parameters
            print("Extracted parameters:", params)
            lowTemp = params['lowTemp']
            highTemp = params['highTemp']
            print('lowTemp = ',lowTemp)
            print('highTemp = ',highTemp)
            saveDataToFile()
        if mode_on == 6:
            if mode != 'on':
                mode = 'on'
                print("on mode")
                turnStoveOn()
                saveDataToFile()
            sendWebPage()                
        elif mode_off == 6:
            if mode != 'off':
                mode = 'off'
                led.off()
                print("off mode")
                turnStoveOff()
                saveDataToFile()
            sendWebPage()
        elif mode_auto == 6:
            mode = 'auto'
            print("auto mode")
            saveDataToFile()
            sendWebPage()
        elif getData == 6:
            #print("temps request")
            sendData()
        elif saveSetting == 6:
            saveDataToFile()
        elif syncOn == 6:
            stoveState = 'on'
            mode = 'on'
            saveDataToFile()
            turnStoveOn()
            sendWebPage()
        elif syncOff == 6:
            stoveState = 'off'
            mode = 'off'
            saveDataToFile()
            turnStoveOff()
            sendWebPage()
        else:
            sendWebPage()
            
    except OSError as e:
        conn.close()
        print('Connection closed')
        

