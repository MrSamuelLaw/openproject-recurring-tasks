# About
Open Project Automation Scripts is a container that can be used to program complex automations such as recurring tasks.

# Recurring Tasks Setup Guide
To setup recurring tasks in open project using the open create the following custom fields inside of the open project instance.  
Custom fields are split into two categories, temporal and weather event.  

Temporal meaning fields are required for creating work packages based on time and work package status.  
Weather event fields are required for creating work packages based on weather events and is built using open-meteo.

* Note that the names of the fields, as well as the options for each field __are__ case sensitive.  
* Also note that the fields should __not__ be required or for all projects, only the projects where the work packages functioning as templates live.

Screen shots of each field are shown for convenience.

Once the fields are created, rename the file .env.example to .env and edit the entries match your setup, then run
```
    docker compose up -d
```
to start the container. Note that valid latitude and longitude values are only required if using the Weather Forecast algorithm.

## Template Work Package Examples
Once the custom fields are in place and activated in the project that will house the template work packages. Creating a recurring work package is as easy as creating a new work package and filling out the fields.  

### Fixed Interval
In the image below, I have created a work package that will be cloned into the project named Main on a fixed interval every 7 days, regardless of the previous iterations status.

![alt text](images/fixed_interval_example.png)

### Fixed Delay
In the image below, I have created a work package that will be cloned into the project named Main on a 28 days after the previous iteration is completed. Put another way on day zero, a new work packages will appear in the project named Main. Once that clone work packages no longer has an open status, a new clone will be created 28 days after the first clone changed to a closed status.

![alt text](images/fixed_delay_example.png)

### Fixed Day Of Month

In the image below, I have created a work package that will be cloned into the project named Main on the 11th of each month. Note that the day must exist in the month, or the work package will not be cloned.

![alt text](images/fixed_day_of_month_example.png)

### Fixed Day Of Year

In the image below, I have created a work package that will be cloned into the project named Main on the 6th of each September every year. Note that the day must exist in the month, or the work package will not be cloned.

![alt text](images/fixed_day_of_year_example.png)

### Weather Forecast

In the image below, I have created a work package that will be clone into the project Main when a weather code between (inclusive) 63 to 67 or 71 to 77 or 81 to 99 is in the forecast for the next 1 days. The template will only be cloned on the rising edge of the forecast intersecting with the desired weather codes. Put another way, if it storms every day for a week, this template will only be created one day before the first storm, as the transition from no storms in the next day to storms in the next day occurs only prior to the first day or stormy weather.

![alt text](images/weather_forecase_example.png)


## Temporal Recurring Fields
Temporal recurring fields are required, as they provide the necessary data for the scripts to calculate dates when creating
new work packages.

* Auto Scheduling Algorithm  
    type: List  
    description/help-text:  
    ```md
    Algorithm to use when automatically creating work packages.

    If Auto Scheduling Algorithm is set to:

    *   **Fixed Interval**:
        
        *   Clones the work package into the target project on the given interval from the work packages start date.
            
    *   &nbsp;**Fixed Delay**:
        
        *   Clones the work package into the target project an interval number of days after the last one is completed.
            
    *   **Fixed Day Of Month:**
        
        *   Clones the work package into the target project project on this day of the month every month (if it has that day)

    *   **Fixed Day Of Year:**

        *   Clones the work package into the target project on the date every year.
            Note, that the date precedence used is start date, then due date, and finally date.
            
    *   **Weather Forecast:**
        
        *   Clones the work package into the target project if the weather codes are found in the forecast within the interval from the current date.   
    ```

    options: 
    - Fixed Interval
    - Fixed Delay
    - Fixed Day Of Month
    - Weather Forecast  
      
    ![alt text](images/auto_scheduling_algorithm.png)

* Interval/Day Of Month  
    type: Integer.  
    description/help-text:  
    ```md
        If Auto Scheduling Algorithm is set to:

    *   &nbsp;**Fixed Interval**:
        
        *   Clones the work package into the target project on the given interval from the work packages start date.
            
    *   **Fixed Delay**:
        
        *   Clones the work package into the target project an interval number of days after the last one is completed.
            
    *   **Fixed Day Of Month:**
        
        *   Clones the work package into the target project project on this day of the month every month (if it has that day)

    *   **Fixed Day Of Year:**

        *  **N/A**
            
    *   **Weather Forecast:**
        
        *   Clones the work package into the target project if the weather codes are found in the forecast within the interval from the current date.k package into the target project if the weather codes are found in the forecast within the interval from the current date.
    ```

    ![alt text](images/interval_day_of_month.png)

* Target Project
    type: List  
    description/help-text:
    ```md
    Project this work package should be cloned into.
    ```
    ![alt text](images/target_project.png)

## Weather Event Recurring Fields (Optional)
Weather event recurring fields are optional and allow the automation scripts to create work packages based on weather events.  

* Weather Codes
    type: Text  
    description/help-text:  
    ```md
        Weather codes for which to create a new weather forecast recurring work package.

    *   If using multiple weather codes, they must be separated by a comma (no spaces), for example, 71, 77
        
    *   If using a range of weather codes, they must be separated by a dash (no spaces), for example, 71-77
        
    *   Multiple selection &amp; ranges can be used together, for example, 71-77,80-82
        

    see [https://open-meteo.com/en/docs](https://open-meteo.com/en/docs) for more info
    ```

    ![alt text](images/weather_codes.png)

* Weather Detected Status
    type: Boolean  
    description/help-text:
    ```md
    Flag that goes true when the weather codes are in the forecast, and false when they are not.

    The auto-scheduling algorithm only generates new work packages when the transition from false to true is detected.

    ```
    ![alt text](images/weather_detected_status.png)