#ability to choose how long you use block heater, size of block heater, how long idle for ICE
#weekend miles
#assume 30mph (or ask?) and subtract off travel time from parked time.
import os
import io
import math
import functools
import urllib
import datetime
import streamlit as st
import pandas as pd
import numpy as np
import requests
from ast import literal_eval
import matplotlib.pyplot as plt

# Most of the data files are located remotely and are retrieved via
# an HTTP request.  The function below is used to retrieve the files,
# which are Pandas DataFrames

# The base URL to the site where the remote files are located
base_url = 'http://ak-energy-data.analysisnorth.com/'


# # Use some of Alan Mitchells's code from the heat pump calculator (github) to download tmy files for hourly temperature

def get_df(file_path):
    """Returns a Pandas DataFrame that is found at the 'file_path'
    below the Base URL for accessing data.  The 'file_path' should end
    with '.pkl' and points to a pickled, compressed (bz2), Pandas DataFrame.
    """
    b = requests.get(urllib.parse.urljoin(base_url, file_path)).content
    df = pd.read_pickle(io.BytesIO(b), compression='bz2')
    return df

@functools.lru_cache(maxsize=50)    # caches the TMY dataframes cuz retrieved remotely
def tmy_from_id(tmy_id):
    """Returns a DataFrame of TMY data for the climate site identified
    by 'tmy_id'.
    """
    df = get_df(f'wx/tmy3/proc/{tmy_id}.pkl')
    return df
st.image(['ACEP.png','AEA Logo 3line Flush Left in Gradient Color.png'])
st.title("Alaska Electric Vehicle Calculator")
st.write("")
st.write("This is a calculator to find out how much it would cost to charge an EV at home in Alaska, and what the carbon emissions would be.")
st.write("A comparison is also made to an internal combustion engine (ICE) vehicle.")


#location
#get the Alaska city data
# Access as a Pandas DataFrame
dfc = get_df('city-util/proc/city.pkl')
#find default electric rate from Alan Mitchell's database which is updated whenever Akwarm library files are updated
dfu = pd.read_csv('https://raw.githubusercontent.com/alanmitchell/akwlib-export/main/data/v01/utility.csv')
#GET THE MOST BASIC DATA NEEDED FOR A SIMPLE INPUT VERSION
#now create a drop down menu of the available communities and find the corresponding TMYid
cities = dfc['aris_city'].drop_duplicates().sort_values(ignore_index = True) #get a list of community names
city = st.selectbox('Select your community (start typing to jump down the list):', cities ) #make a drop down list and get choice
tmyid = dfc['TMYid'].loc[dfc['aris_city']==city].iloc[0] #find the corresponding TMYid

#get the tmy for the community chosen:
tmy = tmy_from_id(tmyid)

#database Temperatures are in F, so will make a celcius column as well, since our energy use relationships use celcius
tmy['T_C'] = (tmy['db_temp'] - 32)*5/9

ev = st.selectbox('Select your vehicle type:', ('car', 'truck' )) #make a drop down list and get choice#choose vehicle type
if ev == 'car':
    epm = .28 #setting the default energy use per mile according to the EPA here!
    #2017 Chevy Bolt is energy per mile (epm) = 28kWh/100mi at 100% range (fueleconomy.gov)
    mpg = 27
    ig = .2 #gas used at idle for ICE equivalent: cars use about .2g/hr or more at idle : https://www.chicagotribune.com/autos/sc-auto-motormouth-0308-story.html
#pickup trucks .4g/hr
if ev == 'truck':
    epm = .5
    mpg = 20
    ig = .4

#find driving distance:
owcommute = (st.slider('How many miles do you drive each day, on average?', value = 10))/2
weekend = owcommute
garage = False

util = dfc['ElecUtilities'].loc[dfc['aris_city']==city].iloc[0][0][1] #find a utility id for the community chosen
if util == 2:
  util =1 #Anchorage maps to ML&P, but want to map to CEA
#choose the PCE rate here:
nonpce = literal_eval(dfu['Blocks'].loc[dfu['ID']==util].iloc[0].replace('nan', 'None'))[0][1]
pce = dfu['PCE'].loc[dfu['ID']==util].iloc[0] #this is the PCE adjustment to the full rate!
if ((pce==pce) and pce > 0):
    PCE = True
 #   coe = nonpce - pce #I used this when I wanted to chose the PCE adjusted rate as the default, but since I am not doing this, don't need it
else:
    PCE = False
   # coe = nonpce
coe = nonpce
#greenhouse gas emissions from electricity:
# Access Alan's Alaska utility data as a Pandas DataFrame
#dfu = get_df('city-util/proc/utility.pkl') #older, non updated emissions
 
cpkwh_default = dfu['CO2'].loc[dfu['ID']==util].iloc[0]/2.2 #find the CO2 per kWh for the community and divide by 2.2 to change pounds to kg
cpkwh_default = float(cpkwh_default)
cpkwh = cpkwh_default
pvkwh = 0 #initialize to no pv kwh...
dpg = st.slider('How many dollars do you pay per gallon of gas?', value = 4.00, max_value = 20.00)
plug = False
idle = 5
garage = False
##############################################################################################
#more complicated input:
complicated = st.checkbox("I would like to check and adjust other factors in this calculation.")
if complicated: 
    weekend = (st.slider('If you drive a different amount on weekends, how many miles do you drive each weekend day, on average?', value = round(owcommute*2,0), max_value = 100.0))/2   
 #add a garage option for overnight parking
    garage = st.checkbox("I park in a garage overnight.")
    if garage:
        Temp_gF = st.slider('What temperature is your garage kept at in the winter?', value = 50, max_value = 80)
        Temp_g = (Temp_gF - 32)*5/9 #put it in C for calculations
   
    epm = st.slider('Enter the Rated kWh/mile of the EV to investigate '
                '(this calculator internally adjusts for the effect of temperature): '
                'check at fueleconomy.gov', value = epm, max_value = 3.0)
    rate = nonpce
    name = dfu.loc[dfu['ID']==util].iloc[0][1]
    name = name.split('-')[0]
    st.write("According to our records, your utility is",name )
    if PCE == True:
        st.write("The PCE-adjusted rate per kWh on record is $",round(nonpce - pce,2))
    st.write("The full residential rate per kWh on record is $",round(nonpce,2))  
    st.write("It is likely that these values are out of date and need to be adjusted - check your electricity bill to update the value below.") 
    coe = st.slider('What do you expect to pay per kWh for electricity to charge your EV?',  value = round(float(rate),2), max_value = 1.50)
    st.write("Note: we do not account for partial coverage of PCE, block rates, or commercial rates and demand charges, which could make the electric costs higher than expected from this simple calculator.")

    st.write("")
    cpkwh = st.slider("How many kg of CO2 are emitted per kWh for your utility "
                  "(if you don't know, leave it at the default value here, which is specific to your community "
                  "but might become out of date."
                  "  Another caveat - the default is based on total utility emissions, but additional electricity may come from a cleaner or dirtier source."
                  "  For instance, in Fairbanks, any new electricity is likely to be generated from Naptha, which is cleaner than the utility average,"
                  "  so a better value to use below for Fairbanks might be 0.54)?:", max_value = 2.0, value = cpkwh_default)
    
    ispv = st.checkbox("I will have solar panels at my home for the purpose of offsetting my EV emissions.")
    if ispv:
        pv = st.slider("How many kW of solar will you have installed? (pro tip: this calculator assumes a yearly capacity factor "
                   "of 10%.  This is reasonable for most of Alaska, but if you are an engineering wiz and want to"
                   " correct this slider for the details of your installation, go ahead!)",
                   max_value = 25.0, value = 3.0)
    #at 10% capacity factor this equation below gives the number of PV kWh generated - we will be kind and
    #attribute them all to the EV, subtracting them off of the emissions
        pvkwh = .1*24*365*pv
        st.write("The annual kWh that your solar panels are estimated to generate:", round(pvkwh,3))
        st.write("We will use this to reduce the carbon emissions from your EV electricity.")

#comparison to gas:
    mpg = st.slider('What is the mpg of your gas vehicle?', value = mpg, max_value = 60)
    
    plug = st.checkbox("I have a block heater on my gas car.")

    if plug:
        st.write("This calculator assumes a block heater is used for your gas car any day the minimum temperature has been less than 20F")
        plug_hrs = st.slider("How many hours do you plug in your block heater each day?", max_value = 24, value = 2)
        plug_w = st.slider("How many watts is your block heater (or block plus oil heater)?", min_value = 400, max_value = 1600)
        #we will also use 20F as the temperature below which idling happens, but could change that with better info, or allow a choice
    idle = st.slider("How many minutes do you idle your car on cold days (to warm up or keep your car warm)?", max_value = 1440, value = 5)
    
#######################################3   
    
# # put together a driving profile

tmy['miles'] = 0
#Assume a 'normal' commute of x miles at 8:30am and 5 miles at 5:30pm M-F
tmy['miles'] = tmy['miles'].where((tmy.index.time !=  datetime.time(8, 30))|(tmy.index.dayofweek > 4),owcommute)
tmy['miles'] = tmy['miles'].where((tmy.index.time !=  datetime.time(17, 30))|(tmy.index.dayofweek > 4),owcommute)
#that took care of times, but now for weekends, use the same times for simplicity:
tmy['miles'] = tmy['miles'].where((tmy.index.dayofweek < 5)|(tmy.index.time !=  datetime.time(8, 30)),weekend)
tmy['miles'] = tmy['miles'].where((tmy.index.dayofweek < 5)|(tmy.index.time !=  datetime.time(17, 30)),weekend)

st.write("Total yearly miles driven:", tmy['miles'].sum())

# assume an average speed to calculate how much of the hour is spent driving vs parked
speed = 30
tmy['drivetime'] = tmy['miles'] / speed  # make a new column for time spent driving in fraction of an hour

# if time is greater than an hour, we need to also mark sequential hours with correct amount
# max miles in a day is currently 100, meaning 50 miles morn and eve - 1.67 hours each, or 8:30am to 10:10am and 17:30 to 19:10
# max idle is 24 hours, apply first between morn and eve driving, then before morning drive, then after eve drive, ignore anything left

for i, t in enumerate(tmy['drivetime']):
    if t > 1:
        tmy.drivetime.iloc[i + 1] = tmy.drivetime.iloc[i + 1] + tmy.drivetime.iloc[i] - 1
        tmy.drivetime.iloc[i] = 1
        
##########################################################################################################
###  This section is to add in the idletime 

tmy['idletime'] = 0

#######Take care of weekdays first:###################
#need to know a breakdown for how idle time compares to other things:
#portion of an hour available for idling at end of morning commute:
startidle = 1 - (owcommute/speed - int(owcommute/speed))
#hour during which this end of morning commute is happening:
start = 8 + int(owcommute/speed)
#time of idle between morn and eve commute:
if idle/60 < 9-owcommute/speed: #make sure everything is in hours!
  between = idle/60 #between is the time between commutes that is spent idling
else:
  between = 9-owcommute/speed

#time of idle before morn commute:
extra = idle/60-between
if extra < 8:
  before = extra
  extraextra = 0
else:
  before = 8
  extraextra = extra - 8


if startidle < idle/60:
  left = between - startidle #how much is left of idle time in hours for in between the commutes
  end = start + 1 + int(left)
  endidle = left-int(left)
  tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(start, 30))|(tmy.index.dayofweek > 4),startidle)
  tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <=  datetime.time(start, 30))|(tmy.index.time >=  datetime.time(end, 30)))|(tmy.index.dayofweek > 4),1)
  tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(end, 30))|(tmy.index.dayofweek > 4),endidle)
else:
  tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(start, 30))|(tmy.index.dayofweek > 4),idle/60)
#if idle is less than the time in between commutes (8:30 + owcommute/speed to 17:30), just need to fill in the hours then
#however if, there is extra time:
if before > 0: #there are more idle hours to add in!
#add it before the morning commute, but only back until 12:30am!
  startbefore = 8 - int(before)
  #either before is 8 and this is 0 and all 1's should go in, 
  #or before is less than 8 and this is a time where the hour before might have a value < 1
  tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <  datetime.time(startbefore, 30))|(tmy.index.time >=  datetime.time(8, 30)))|(tmy.index.dayofweek > 4),1)
  if before - int(before) > 0: #this means two things - there is a remainder to add and also the startbefore is not before 12:30am
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(startbefore-1, 30))|(tmy.index.dayofweek > 4),before - int(before))
#and now if there is no extraextra, we are done, but if there is we need to add that!
if extraextra > 0:
  #idle time to start after eve commute
  starteve = 17+int(owcommute/speed)
  if extraextra < startidle: #just a little idling to throw after the eve commute!
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(starteve, 30))|(tmy.index.dayofweek > 4),extraextra)
  else:
    left = extraextra - startidle #how much is left of idle time in hours after the commutes
    end = starteve + 1 + int(left)
  
    if end <= 23:
      endidle = left-int(left)
    else:
      end = 23
      endidle = 1
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(starteve, 30))|(tmy.index.dayofweek > 4),startidle)
    tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <=  datetime.time(starteve, 30))|(tmy.index.time >=  datetime.time(end, 30)))|(tmy.index.dayofweek > 4),1)
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(end, 30))|(tmy.index.dayofweek > 4),endidle)

#NOW need to do this for weekends too!
#first, if there is no driving on the weekends, don't put in any idle!!
if weekend > 0:
#need to know a breakdown for how idle time compares to other things:
#portion of an hour available for idling at end of morning commute:
  startidle = 1 - (weekend/speed - int(weekend/speed))
#hour during which this end of morning commute is happening:
  start = 8 + int(weekend/speed)
#time of idle between morn and eve commute:
  if idle/60 < 9-weekend/speed: #make sure everything is in hours!
    between = idle/60 #between is the time between commutes that is spent idling
  else:
    between = 9-weekend/speed
#time of idle before morn commute:
  extra = idle/60-between
  if extra < 8:
    before = extra
    extraextra = 0
  else:
    before = 8
    extraextra = extra - 8


  if startidle < idle/60:
    left = between - startidle #how much is left of idle time in hours for in between the commutes
    end = start + 1 + int(left)
    endidle = left-int(left)
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(start, 30))|(tmy.index.dayofweek < 5),startidle)
    tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <=  datetime.time(start, 30))|(tmy.index.time >=  datetime.time(end, 30)))|(tmy.index.dayofweek < 5),1)
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(end, 30))|(tmy.index.dayofweek < 5),endidle)
  else:
    tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(start, 30))|(tmy.index.dayofweek < 5),idle/60)
#if idle is less than the time in between commutes (8:30 + owcommute/speed to 17:30), just need to fill in the hours then
#however if, there is extra time:
  if before > 0: #there are more idle hours to add in!
  #add it before the morning commute, but only back until 12:30am!
    startbefore = 8 - int(before)
    #either before is 8 and this is 0 and all 1's should go in, 
    #or before is less than 8 and this is a time where the hour before might have a value < 1
    tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <  datetime.time(startbefore, 30))|(tmy.index.time >=  datetime.time(8, 30)))|(tmy.index.dayofweek < 5),1)
    if before - int(before) > 0: #this means two things - there is a remainder to add and also the startbefore is not before 12:30am
      tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(startbefore-1, 30))|(tmy.index.dayofweek < 5),before - int(before))
#and now if there is no extraextra, we are done, but if there is we need to add that!
  if extraextra > 0:
  #idle time to start after eve commute
    starteve = 17+int(owcommute/speed)
    if extraextra < startidle: #just a little idling to throw after the eve commute!
      tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(starteve, 30))|(tmy.index.dayofweek < 5),extraextra)
    else:
      left = extraextra - startidle #how much is left of idle time in hours after the commutes
      end = starteve + 1 + int(left)
  
      if end <= 23:
        endidle = left-int(left)
      else:
        end = 23
        endidle = 1
      tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(starteve, 30))|(tmy.index.dayofweek < 5),startidle)
      tmy['idletime'] = tmy['idletime'].where(((tmy.index.time <=  datetime.time(starteve, 30))|(tmy.index.time >=  datetime.time(end, 30)))|(tmy.index.dayofweek < 5),1)
      tmy['idletime'] = tmy['idletime'].where((tmy.index.time !=  datetime.time(end, 30))|(tmy.index.dayofweek < 5),endidle)

############################################################################################
#ok, now we've got the idletime marked, so we can calculate the (non-idle) parked time:

tmy['parktime'] =1- tmy['drivetime'] - tmy['idletime']

tmy['t_park'] = tmy['T_C'] # set the default parking temp to the outside temp - in C
if garage:
    # where the time is at or after 8:30 and before or at 17:30, parking temp is default, otherwise it is garage temp if garage temp < outside temp:
    tmy['t_park'] = tmy['t_park'].where(
        ((tmy.index.time >= datetime.time(8, 30)) & (tmy.index.time <= datetime.time(17, 30)))|(tmy.t_park > Temp_g), Temp_g)

# # Use the relationship between temperature and energy use to find the total parked energy use


#from an analysis of the data of 3 Bolts in southcentral Alaska, energy to condition battery while parked, while plugged in: 
# parke (kWh/hr) = -.015 * Temp(C) + .26 , and not less than 0

tmy['parke'] = tmy['t_park'] * -.015 + .26
tmy['parke'] = tmy['parke'].where(tmy['parke'] > 0,0) #make sure this isn't less than zero! Could just do this once, below...

#Data from an Anchorage Bolt shows a different trend for an UNPLUGGED park. Preliminary data shows the following:
#it is unknown if this is general to all vehicles or just the Bolt.
# parke (kWh/hr) = -.006 * Temp(C) + .12 , and not less than 0
#we will assume the vehicle is plugged in at night and unplugged during the day.  This is a big assumption and should allow for
#adjustment in the future!!
# where the time is at or after 8:30 and before or at 17:30, parke follows the fit to the unplugged Bolt data: 
tmy['parke'] = tmy['parke'].where(
        ((tmy.index.time <= datetime.time(8, 30)) | (tmy.index.time >= datetime.time(17, 30))), tmy['t_park'] * -.006 + .12)
tmy['parke'] = tmy['parke'].where(tmy['parke'] > 0,0) #make sure this isn't less than zero!

#I have some derived data from 4 Alaskan Teslas as well, which broadly cooberates the Bolt data above, hopefully all of this will soon be
#published so I can just refer to that here


tmy['parke'] = tmy['parke']*tmy['parktime'] #adjusted for amount of time during the hour spent parked


#FOR WARM IDLE - we now have trends for idling the Anchorage Bolt, and a few data points for two north slope Lightnings (some derived Tesla data also
#seems to be in broad agreement). More data is needed, but at this time the fit to the combined data from the Bolt and Lightnings is: 
#-0.163 * T(C) + 3.10 but not less than 0,
# the maximum in the data is ~7.56kWh/hr, but doesn't extend colder than about -25C.
#we do expect a maximum at some point as heating systems run full blast...
#(this forum says that 7kw is the max power of the Bolt heater: https://www.chevybolt.org/threads/how-long-can-a-bolt-battery-sustain-cabin-heat.37519/)

tmy['idlee'] = tmy['t_park'] * -.163 + 3.10 #from Anchorage Bolt and N Slope F150 data
tmy['idlee'] = tmy['idlee'].where(tmy['idlee'] > 0, 0) #min of 0kW
tmy['idlee'] = tmy['idlee'].where(tmy['idlee'] < 7.56, 7.56) #max of 7.56 kWh/hr, highest seen in N. Slope lightning data
tmy['idlee'] = tmy['idlee']*tmy['idletime']#adjusted for amount of time during the hour spent idling


st.write("") #adding some spaces to try to keep text from overlapping


#the below is code that finds the energy use of an EV based on the ambient temperature, according to published data
#(including that from this author from Alaska EVs, see: A Global Daily Solar Photovoltaic Load 
#Coverage Factor Map for Passenger Electric Vehicles, M Wilber, E Whitney, C Haupert, 2022 IEEE PES/IAS PowerAfrica, 1-4
#From this paper, the relationship between relative efficiency and T for passenger cars is: RE = .000011T^3 + .00045T^2 - 0.038T + 1.57, T in C

#from some preliminary north slope Lightning data we have, it seems that the higher order terms/slope does not scale with the EPA rated
#efficiency, just the intercept.  This makes sense as the cabin size to heat is similar to a car (the battery is bigger though,
#so it might require more heat?) anyway, the below fits the data we have from the truck better:
#tmy['EpM_T'] = .28/1.15 *(.000011*tmy['T_C']**3 + .00045*tmy['T_C']**2 - 0.038*tmy['T_C']) + epm/1.15 * 1.57
#carrying through the math:
tmy['EpM_T'] = .0000027*tmy['T_C']**3 + .000011*tmy['T_C']**2 - 0.00093*tmy['T_C'] + epm * 1.37

#energy use: 
tmy['kwh']= tmy['EpM_T']*tmy['miles']
         
#add on the energy use while parked and idling:
tmy['kwh'] = tmy.kwh + tmy.parke + tmy.idlee


#total cost to drive EV for a year:

total_cost_ev = coe*tmy.kwh.sum()


#make the mpg of the gas vehicle temperature dependent too like above.
#according to fueleconomy.gov, an ICE can have 15 to 25% lower mpg at 20F than 77F. the 25% is for trips under 3-4 miles, so could adjust the below later for this
#for now I am just using 20% less
tmy['mpg'] = mpg
tmy['mpg'] = tmy['mpg'].where((tmy['db_temp'] > 77), mpg - .2*mpg*(77-tmy['db_temp'])/57) #using the Temperature in F column for this calc

tmy['gas'] = tmy.miles/tmy.mpg #gallons of gas used for driving a gas car

#################################
# add gas from idling in the cold
############################
#cars use about .2g/hr or more at idle : https://www.chicagotribune.com/autos/sc-auto-motormouth-0308-story.html
#pickup trucks .4g/hr

idleT = 19 #note this is in C and is equivalent to 66F. We will set idle energy use to 0 above this, assuming that at warmer temps people are 
#less likely to leave an engine running, even though energy for AC is likely at warm temperatures or in sunny conditions. This is set to match the 0 point in EV data as well.
tmy['idleg'] = 0
tmy['idleg'] = tmy['idleg'].where(tmy['t_park'] > idleT, ig) #only idle when less than idle Temperature set above 
tmy['idleg'] = tmy['idleg']*tmy['idletime']#adjusted for amount of time during the hour spent idling
tmy['gas'] = tmy['gas'] + tmy['idleg']

total_cost_gas = tmy.gas.sum()*dpg

#what about the engine block heater? Doing the calculations below woth Temperature in F.
tmy_12 = tmy[['db_temp']].resample('D', label = 'right').min() 
tmy_12['plug'] = 0
tmy_12['plug'] = tmy_12['plug'].where(tmy_12.db_temp > 20, 1)
plug_days = tmy_12.plug.sum()

if plug:
    kwh_block = plug_w/1000*plug_hrs*plug_days
else:
    kwh_block = 0
cost_block = coe*kwh_block


#now look at ghg emissions:
#Every gallon of gasoline burned creates about 8.887 kg of CO2 (EPA)

ghg_ice = 8.887*tmy.gas.sum()

ghg_ev = cpkwh*(tmy.kwh.sum() - pvkwh)
if ghg_ev < 0:
    ghg_ev = 0

ghg_block = cpkwh*kwh_block

st.write("")


st.write("Total cost of Electric Vehicle fuel per year = $", round(total_cost_ev,0))
st.write("Total cost of Internal Combustion Engine (gas) fuel per year = $", round(total_cost_gas+cost_block,0))
st.write("Total kg CO2 emissions of Electric Vehicle per year = ", round(ghg_ev,0))
st.write("Total kg CO2 emissions of Internal Combustion Engine per year = ", round(ghg_ice + ghg_block,0))
st.write("")
st.write("Note that costs and emissions for the Internal Combustion Engine vehicle include gas and any electricity used for block/oilpan/etc heating.")
st.write("")
x = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
tmy_month = tmy.resample('M').sum()
fig, ax = plt.subplots()
ax.bar(x,tmy_month.kwh, width=0.35, align='edge', label = 'EV')

    
# Add the axis labels
ax.set_xlabel('Month')
ax.set_ylabel('EV Energy Use in kWh')

# Add in a legend and title
#ax.legend(loc = 'upper right')
#ax.title('')
st.pyplot(fig)
st.write("")       
st.write("The effective yearly average kWh/mile for your EV is calculated as ", round(tmy.kwh.sum()/tmy.miles.sum(),2))
st.write("This is a lower efficiency than the rated kWh/mile - cold temperatures lower the range and driving efficiency, and also lead to energy use to keep the battery warm while parked. ")

st.write(" ")

st.write("This project was made possible by funding from the Alaska Energy Authority, Office of Naval Research (ONR) Award # N00014-18-S-B001, and the National Science Foundation’s Navigating the New Arctic program’s “Planning Collaborative Research: Electric Vehicles in the Arctic” project (award # 2127171) ")

st.write("The calculations are based on data for commercially available electric cars, results may not hold for other types of electric vehicles. ")
st.write("Your personal driving habits and other real world conditions could change these results dramatically! ")
st.write("The underlying model relating energy use with temperature will be updated as we continue to collect cold weather EV data. ")
st.write("Thanks to Alan Mitchell of Analysis North for Alaskan utility data, tmy files, and wonderful code to access and use them all.")
st.write("Community and Utility data are taken from http://ak-energy-data.analysisnorth.com/ and https://raw.githubusercontent.com/alanmitchell ")
st.write("See also https://github.com/alanmitchell/heat-pump-calc")
st.write("...And definitely check out the Alaskan Heat Pump Calculator at https://heatpump.cf to see if you should get a heat pump!")
st.write("")
st.write("")
st.write("Please peak under the hood at this code.  Basically, a typical year's hourly temperature profile is combined with a daily driving profile and realtionships between the energy use for driving and maintaining the EV while parked vs temperature to arrive at a cost and emissions for the kWh needed by the EV.")
st.write("email Michelle Wilber at mmwilber@alaska.edu with any suggestions or comments.")
