package org.mosip.ussd.service;

import java.util.List;
import java.util.Optional;

import org.mosip.ussd.entity.Resident;
import org.mosip.ussd.storage.ResidentRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;


@Service
public class ResidentService {
  
    @Autowired
    ResidentRepository residentRepository;
    
    private static final Logger logger = LoggerFactory.getLogger(ResidentService.class);
   
    public Resident addResident(Resident resident){
      
        
        logger.info("Id="+resident.getId() +","+ resident.getVID() + ",lang=" + resident.getPrefLang());

        return  residentRepository.saveAndFlush(resident);

        
    }
    public int updateResidentLangCode(String phoneNo, String lcode){
        int retVal = -1;

        Optional<Resident> result = residentRepository.findById(phoneNo);
        if(!result.isPresent()){
            Resident resident = new Resident();
            resident.setId(phoneNo);
            resident.setPrefLang(lcode);
            addResident(resident);
            retVal = 1;
        }
        else
            retVal =  residentRepository.updateResidentLangCode(phoneNo, lcode);
        return retVal;
    }
    public int updateResidentUin(String phoneNo, String uin){
        int retVal = -1;

        Optional<Resident> result = residentRepository.findById(phoneNo);
        if(!result.isPresent()){
            Resident resident = new Resident();
            resident.setId(phoneNo);
            resident.setVID(uin);
            addResident(resident);
            retVal = 1;
        }
        else
            retVal =  residentRepository.updateResidentUIN(phoneNo, uin);
        return retVal;
    }
    public Resident updateResident(String phoneNo, String lcode){

        Resident r = getResident(phoneNo);
        if(r != null){
            r.setPrefLang(lcode);
            return residentRepository.saveAndFlush(r);
        }
        else
        return null;
    }
    public Resident getResident(String mobileNo){
       
        Optional<Resident> ret  = residentRepository.findById(mobileNo);
        if(ret.isPresent())
            return ret.get();
        else
            return null;
        //.getOne(partnerId);
       
    }
    public List<Resident> getAllResidents(){

        List<Resident> residents = residentRepository.findAll();
       
        return residents;
    }
}
