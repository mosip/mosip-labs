package org.mosip.ussd.service;
import org.mosip.ussd.storage.PartnerRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;


import java.util.List;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import org.mosip.ussd.entity.Partner;
@Service
public class PartnerService {
  
    @Autowired
    PartnerRepository partnerRepository;
    
    private static final Logger logger = LoggerFactory.getLogger(PartnerService.class);
   
    public Partner addPartner(Partner partner){
      
        
        logger.info("Id="+partner.getId() +","+ partner.getPartnerUrl());

        return  partnerRepository.saveAndFlush(partner);

        
    }
    public Boolean deletePartner(String partnerId){
        partnerRepository.deleteById(partnerId);
        return true;
    }
    public Partner getPartner(String partnerId){
       
        Optional<Partner> ret  = partnerRepository.findById(partnerId);
        if(ret.isPresent())
            return ret.get();
        else
            return new Partner();
        //.getOne(partnerId);
       
    }
    public List<Partner> getAllPartners(){

        List<Partner> partners = partnerRepository.findAll();
       
        return partners;
    }
}
