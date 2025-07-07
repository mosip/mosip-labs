package org.mosip.ussd.sm.models;

import lombok.Data;

@Data
public class SMTransistionModel {
    String id;
    String from;
    String to;
    String evttype;
    String evtvalue;
    String tag;
 //   SMVariable condition;
    SMCondition condition;
    String saveto; //variable name : save input text to specified variable, so it will be available in to state
}
