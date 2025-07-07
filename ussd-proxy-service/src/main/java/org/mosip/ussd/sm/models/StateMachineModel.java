package org.mosip.ussd.sm.models;
import java.util.List;
import lombok.Data;

@Data
public class StateMachineModel {
  
    String name;
    String servicecode;
    List<SMStateModel> states;
    List<SMTransistionModel> transitions;
   
}
