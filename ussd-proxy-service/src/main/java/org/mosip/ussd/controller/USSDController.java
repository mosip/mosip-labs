package org.mosip.ussd.controller;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

import javax.annotation.PostConstruct;
import javax.xml.parsers.ParserConfigurationException;

import org.mosip.ussd.model.ATUSSDRequest;
import org.mosip.ussd.service.CredentialClaimsService;
import org.mosip.ussd.service.CredentialService;
import org.mosip.ussd.service.PartnerService;
import org.mosip.ussd.service.ResidentService;
import org.mosip.ussd.service.SMContextService;
import org.mosip.ussd.service.XMLRPCService;
import org.mosip.ussd.sm.SMProcessor;
import org.mosip.ussd.sm.models.AppConfig;

import org.mosip.ussd.util.Util;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.xml.sax.SAXException;

@RestController
public class USSDController {
    @Value( "${mosip.appId}" )
	private String appId;
	@Value( "${mosip.clientId}" )
	private String clientId;
	@Value( "${mosip.clientSecret}" )
	private String clientSecret;
	@Value("${mosip.baseUrl}")
	private String baseUrl;
	@Value ("${mosip.useCredsAPI}")
	Boolean useCredsAPI;
    @Value("${mosip.stoplightBaseUrl}")
	private String stoplightBaseUrl;
	
	@Value("${mosip.credServiceBaseUrl}")
	private String credServiceBaseUrl;
	
    @Value("${mosip.ussd.statemachine.file}")
    private String SMJasonFile;
    
    @Value("${mosip.ussd.languages}")
    private String[] langPreferences;

   @Autowired
   SMContextService ctxService;

   @Autowired
   CredentialClaimsService credentialClaimsService;
   @Autowired
   CredentialService credentialService;
   @Autowired
   PartnerService partnerService;
   @Autowired
   ResidentService residentService;

   @Autowired
   @Qualifier("simpleJobLauncher")
   JobLauncher jobLauncher;
   @Autowired
   Job job;

   private static final Logger logger = LoggerFactory.getLogger(USSDController.class);
   
    @Autowired
    XMLRPCService xmlrpcService;

   SMProcessor processor;
   @PostConstruct
   public void initialize(){
        processor = new SMProcessor(ctxService);
        ctxService.cleanUp();
        
        Map<String,String> args = setup();

        AppConfig config = new AppConfig();
        config.Init(args);
        config.setCredentialClaimsService(credentialClaimsService);
        config.setCredentialService(credentialService);
        config.setPartnerService(partnerService);
        config.setResidentService(residentService);
        config.setCtxService(ctxService);
  
        config.setJob(job);
        config.setJobLauncher(jobLauncher);
        
        processor.Init(args,config);
      
   }
   public Map<String,String> setup(){
   
    Map<String,String> args = new HashMap<String,String>();
        args.put("appId", appId);
        args.put("clientId", clientId);
        args.put("clientSecret", clientSecret);
        args.put("ResidentAPIBaseUrl", baseUrl);
        args.put("useCredsAPI", useCredsAPI.toString());
        args.put("credServiceBaseUrl",credServiceBaseUrl);
        args.put("SMJasonFile",SMJasonFile);
        String langList = String.join(",", langPreferences);
        args.put("langPreferences",langList);
        args.put("stoplightBaseUrl",stoplightBaseUrl);
        //serviceProvider.setup(args);
        //configServiceProvider.setup(args);
        
        return args;
    }

    

    @PostMapping(
			path = "/ussd/callback",
			consumes = "application/x-www-form-urlencoded")
    public String handleUSSDRequest(@RequestBody MultiValueMap<?, ?> paramMap) throws Exception {
		String retVal = null;
        ATUSSDRequest request = paramToRequest(paramMap);
        //SMProcessor processor = new SMProcessor(ctxService);
        //processor = new SMProcessor(ctxService);
        //processor.Init();

        processor.load(request.getSessionId());
        processor.getContext().getSessionManager().put("mobileNo", request.getPhoneNumber());
        retVal = processor.execute(request.getText(), request.getServiceCode(), request.getSessionId());
        processor.getContext().save();
        return retVal;
    }

    
    @PostMapping(
			path = "/ussd/xmlrpc/handleRequest")
    public String handleUSSDRequest(@RequestBody String  xmlRequest)  {
        String xmlResponse = "";
        String retVal = null;
    
        logger.info("handleUSSDRequest "+ xmlRequest);

        try {
            ATUSSDRequest request = xmlrpcService.parseRequest(xmlRequest);
            logger.info("handleUSSDRequest "+ request);
            processor.load(request.getSessionId());
            processor.getContext().getSessionManager().put("mobileNo", request.getPhoneNumber());
            retVal = processor.execute(request.getText(), request.getServiceCode(), request.getSessionId());
            processor.getContext().save();
        
            xmlResponse = xmlrpcService.handleRequest(request,retVal);
        } catch (ParserConfigurationException | SAXException | IOException e) {
           
            e.printStackTrace();
        }

        return xmlResponse;

    }

    ATUSSDRequest paramToRequest(MultiValueMap<?, ?> paramMap){
        
        ATUSSDRequest request = new ATUSSDRequest();
		
        paramMap.forEach( (k,v) -> {
            String val ="";
            if(v != null && !v.isEmpty()){
                val = v.get(0).toString();
                val = Util.stripExtra(val);
                
            }
            if(k.equals("text")){
                val = Util.lastPart(val);
                request.setText(val);
            }
            else
            if(k.equals("networkCode"))
                request.setNetworkCode(val);
            else
            if(k.equals("phoneNumber"))
                request.setPhoneNumber(val);
            else
            if(k.equals("sessionId"))
                request.setSessionId(val);
            else
                if(k.equals("serviceCode"))
                    request.setServiceCode(val);
                
        });
        return request;    
      
    }
	
}
/*
 * {
  "text": {""},
  "sessionId": {"1234567"},
  "serviceCode": {"*391*1952"},
  "phoneNumber": {"9845024662"}
}
 */