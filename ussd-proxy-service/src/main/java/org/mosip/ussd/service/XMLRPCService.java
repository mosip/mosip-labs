package org.mosip.ussd.service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;

import java.util.Properties;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;


import org.mosip.ussd.model.ATUSSDRequest;
import org.mosip.ussd.util.Util;
import org.springframework.stereotype.Service;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;
@Service
public class XMLRPCService {
   
    public ATUSSDRequest parseRequest(String xmlRequest) throws ParserConfigurationException, SAXException, IOException{
        ATUSSDRequest req = new ATUSSDRequest();

        final DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        StringBuilder xmlStringBuilder = new StringBuilder();
        xmlStringBuilder.append(xmlRequest);
        ByteArrayInputStream input = new ByteArrayInputStream(xmlStringBuilder.toString().getBytes("UTF-8"));
        Document doc = builder.parse(input);
        Element root = doc.getDocumentElement();
        NodeList members = root.getElementsByTagName("member");
        Properties props = parseMembers(members);
        req.setSessionId(props.getProperty("TransactionId"));
        req.setPhoneNumber(props.getProperty("MSISDN"));
        String resp = props.getProperty("response");
        if(resp == null || resp.equals("true"))
            req.setText(props.getProperty("USSDRequestString"));
        req.setServiceCode(props.getProperty("USSDServiceCode"));

        return req;
    }
    private Properties parseMembers(NodeList members){
        Properties props = new Properties();
        for(int i=0; i<members.getLength(); i++){
            String val="";
            Element param = (Element) members.item(i);
            NodeList values = param.getElementsByTagName("value");
            String key = param.getElementsByTagName("name").item(0).getTextContent();
            System.out.println("key="+key);
            for(int j=0; j< values.getLength(); j++){
                Element value = (Element) values.item(j);
               // if(value != null && value.getChildNodes().getLength()> 1){
                NodeList valList = value.getChildNodes();
                for(int k=0; k <  valList.getLength(); k++){
                    Element valchild = (Element)valList.item(k);
                    //Node valchild = value.getChildNodes().item(1);
                    if(valchild != null){
                        System.out.println(valchild.getNodeName());
                        System.out.println(valchild.getTextContent());
                        val = valchild.getTextContent();
                        break;
                    }
                }
            } 
           // System.out.println(value.getAttribute("string"));
         
            //String value = values.item(0).getFirstChild(). getNodeValue();
            
           props.setProperty(key, val);
        }
        return props;        
    }
    public String handleRequest(ATUSSDRequest request, String response) throws IOException{
        String action = "Continue";
        String trTime = Util.getUTCDateTime(null);
        String trId = request.getSessionId();
       
        if(response != null && !response.isEmpty() ){
            if(response.startsWith("CON"))
                action = "request";
            else 
                action = "end";
            response = response.substring(4);
        }
        InputStream input = XMLRPCService.class.getResourceAsStream("/xmlHandleResponse.xml");
        String xmlResponseTemplate = new String(input.readAllBytes());
        String xmlResponse = String.format(xmlResponseTemplate, 
         response,
         action,
         trTime,
         trId);
       return xmlResponse; 
    }
/*     public static void main(String[] args) throws ParserConfigurationException, SAXException, IOException {
        InputStream input = XMLRPCService.class.getResourceAsStream("/xmlHandleRequest.xml");
        
        String xmlRequest = new String(input.readAllBytes());
        XMLRPCService service = new XMLRPCService();
        System.out.println(xmlRequest);
        ATUSSDRequest req = service.parseRequest(xmlRequest);
        System.out.println(req);
    }
    */
}
