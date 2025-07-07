package org.mosip.ussd.controller;

import java.util.List;

import org.mosip.ussd.entity.Partner;

import org.mosip.ussd.service.PartnerService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;


import org.springframework.http.MediaType;

@RestController
public class PartnerController {
    @Autowired
    PartnerService partnerService;

    @PostMapping(path ="/ussd/partner/",
    headers = {"content-type=application/json" },
    consumes = MediaType.APPLICATION_JSON_VALUE)
	public Partner addPartner(@RequestBody Partner partner){

            return partnerService.addPartner(partner);

	}
    @GetMapping(path ="/ussd/partner/")
	public List<Partner> getAllPartners(){

        return partnerService.getAllPartners();

    }
    /**
     * @param partnerId
     * @return
     */
    @GetMapping(path ="/ussd/partner/{partnerId}")
	public Partner getPartner(@PathVariable(name="partnerId") String partnerId){

        return partnerService.getPartner(partnerId);

    }
    @DeleteMapping(path="/ussd/partner/{partnerId}")
    public Boolean deletePartner(@PathVariable(name="partnerId") String partnerId){
       return  partnerService.deletePartner(partnerId);
    }
    
}
