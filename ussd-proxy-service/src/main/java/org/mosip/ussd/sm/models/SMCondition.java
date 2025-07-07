package org.mosip.ussd.sm.models;

import lombok.Data;
/*
 * Trasnition condition
 * If named variable value matches with specified variable value as per the operation(=,<>,null), 
 * execute the state name specified in toState
 */
@Data
public class SMCondition {
   SMVariable variable;
   String operation;
   String toState; 
}
