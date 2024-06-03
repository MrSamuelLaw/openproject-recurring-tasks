# About
Open Project Automation Scripts is a container that can be used to program complex automations such as recurring tasks.

# Recurring Tasks Setup Guide
To setup recurring tasks in open project using the open create the following custom fields inside of the open project instance.  

* Note that the names of the fields, as well as the options for each field __are__ case sensitive.  
* Also note that the fields should __not__ be required or for all projects.  

Screen shots of each field are shown for convenience.

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
            
    *   **Fixed Delay**:
        
        *   Clones the work package into the target project an interval number of days after the last one is completed.
            
    *   **Fixed Day Of Month:**
        
        *   Clones the work package into the target project project on this day of the month every month (if it has that day)
            
    *   **Weather Forecast:**
        
        *   Clones the work package into the target project if the weather codes are found in the forecast within the interval from the current date.
    ```
    options: 
    - Fixed Interval
    - Fixed Delay
    - Fixed Day Of Month
    - Weather Forecast  
      
    ![alt text](images/auto_scheduling_algorithm.png)

* Interval/Day Of Month of type Integer.  

    ![alt text](images/interval_day_of_month.png)

* Target Project of type List. The options should be a list of project names that a "template" work package can be cloned into.  

    ![alt text](images/target_project.png)

## Weather Event Recurring Fields (Optional)
Weather event recurring fields are optional and allow the automation scripts to create work packages based on weather events.  

* Weather Codes of type Text.  

    ![alt text](images/weather_codes.png)

* Weather Detected Status of type Boolean.

    ![alt text](images/weather_detected_status.png)