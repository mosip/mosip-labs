package org.mosip.ussd.sm.models;
import lombok.Data;

@Data
public class SMStateModel {
   String name;
   String menu;
   String position;
   String handler;
   String saveto; //save input text to specified variable
//   List<SMVariable> variables;       
}
