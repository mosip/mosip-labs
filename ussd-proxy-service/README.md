# UssdProxyService
Bridge between Service Provider/Aggregater's USSD Gateway and ID Provider services.
Current Implementation is a bridge between Africa Talking aggregator's USSD Gatewey and MOSIP  Resident Services.
Reference : https://africastalking.com
Tested using the sandbox. 
An account is registered and two channels created
 service code  *384*19351#  - ID functionalities
 service code  *384*19352#  - Resident preferences configuration
 
Application is tested using the Phone simulator provided by AfricaTalking.
https://developers.africastalking.com/simulator

Upstream Integration
--------------------
With USSD Gateway

Downstream Integration
------------------------
Integration with Resident APIs
IdServiceProvider/IDSAPI.java
Integration with Mimoto
IdServiceProvider/IDCredsAPI.java

Menus for the Dialog
---------------------
Language specific menues defined in resources/2 letter lang code/menu.json
Example : English menues resources/en/menu.json
          Frensh menues  resources/fr/menu.json

State Machines
---------------
One or more state machines be defined in resources/statemachine/sm.json
Machine moves from one state to another based on which transition is  executed
Transition is applied based on the matching creteria

Hierarchy:
 List of Machines
    For each machine define
      name :  a unique name given to each state
      service code
      List of states
      list of transistions

    State
     Consists of 
      name : unique name given to each state
      menu: name of the menu as per listed in meu json
      position: entry | nonentry | end
      handler : the java class which will be invoked when the state machine enters the state
    Transition
     Consists of
        id      : unique id string
        from    : Current state of state machine 
        to      : Next state to which transitioned if this transition executed
        evttype : input | auto
        evtvalue: for event type 'input' this containe the input value
        tag     : name of the state 
        condition: variable value based conditional flow
          variable object : name and expected value of a variable
          operation       : if the variable value matches with the condition as per this operation
                            values =  null |<> | =
          toState         : State to which current execution should shift if the condition matches
        saveto   : variable name to which input text value to be saved. When the execution enters this state first 


Workflows
--------------------
This provides an overview of three workflows implemented using MOSIP APIs from Stoplight. These workflows involve resident identity (RID) and unique identification number (UIN) operations.

## Workflow 1: RID-based Operations

### Steps:
1. **Menu Selection**
   - Navigate to the "Get RID Status" workflow.

2. **Request OTP**
   - Generate OTP based on the Resident ID (RID).
   - [MOSIP Documentation - RID Check Status](https://mosip.stoplight.io/docs/resident/cb5aec5ae467b-rid-check-status)

3. **Check RID Status**
   - Verify the status of the RID using the generated OTP.
   - [MOSIP Documentation - RID Check Status](https://mosip.stoplight.io/docs/resident/cb5aec5ae467b-rid-check-status)


## Workflow 2: UIN-based Operations

### Steps:
1. **Menu Selection**
   - Initiate the "Check UIN Status" workflow.

2. **Request OTP**
   - Generate OTP for the given UIN.
   - [MOSIP Documentation - Validate OTP for Given UIN](https://mosip.stoplight.io/docs/resident/b08fe0d0e35d2-validate-otp-for-given-uin-vid-using-ida-to-verify-phone-email)

3. **Verify UIN Status**
   - Confirm the status of the UIN using the generated OTP.
   - [MOSIP Documentation - Auth Lock Status](https://mosip.stoplight.io/docs/resident/2229d1317ece0-auth-lock-status)


## Workflow 3: UIN Lock/Unlock

### Steps:
1. **Menu Selection**
   - Initiate the "Lock/Unlock UIN" workflow.

2. **Lock/Unlock UIN**
   - Unlock/Lock the previously locked/unlocked UIN.
   - [MOSIP Documentation - Auth Lock/Unlock](https://mosip.stoplight.io/docs/resident/0c178333f2164-auth-lock-unlock)


## Additional Notes:
- Ensure proper authentication and authorization for accessing MOSIP APIs.
- Refer to the provided MOSIP documentation links for detailed API specifications.


       
        
      
           