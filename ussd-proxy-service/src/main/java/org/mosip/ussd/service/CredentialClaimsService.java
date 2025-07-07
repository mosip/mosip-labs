package org.mosip.ussd.service;

import java.time.LocalDate;
import java.time.Period;
import java.time.format.DateTimeFormatter;

import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import org.mosip.ussd.entity.Credentials;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class CredentialClaimsService {
    private static final Logger logger = LoggerFactory.getLogger(CredentialClaimsService.class);

    CredentialService credentialService;
    String vc;
    JSONObject subjJson;

    public CredentialClaimsService(CredentialService service){
        credentialService = service;
    }
    void load(Long crId){
        Credentials cred = credentialService.getCredential(crId);
        if(cred != null){
            String credStr = cred.getContent();
           // logger.info("load: gor credStr:" + credStr);
            try {
                JSONParser parser = new JSONParser();
                JSONObject credsJson = (JSONObject) parser.parse(new String(credStr));
                for(Object k: credsJson.keySet()){
                    logger.info("key="+ k.toString());
                }
                credsJson = (JSONObject)credsJson.get("verifiableCredential");

                subjJson = ((JSONObject)credsJson.get("credentialSubject"));
                logger.info("subjJson:"+ subjJson);
            } catch (ParseException e) {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
			//JSONObject credObject= (JSONObject) credsJson.get("credential");
            
        }
    }
    int computeAge(LocalDate dob){
        LocalDate curDate = LocalDate.now()  ;
        return Period.between(dob, curDate).getYears();
    }
    public Boolean isAgeBetween(Long crId, int min, int max){
        load(crId);
        if(subjJson != null){
            String dob = subjJson.get("dateOfBirth").toString();
            logger.info("dob="+ dob);
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy/MM/dd");
            if(dob.length() <=4) //only year
                dob += "/01/01";
            LocalDate dateBirth = LocalDate.parse(dob, formatter);
                //LocalDate dateBirth =new SimpleDateFormat("yyyy/MM/dd").parse(dob).;
            logger.info("dateBirth="+ dateBirth.toString());
            int age = computeAge(dateBirth);
            logger.info("Age="+ age);
            if(age >=min && age <=max)
                return true; 

        }
        return false;
    }


    
}
