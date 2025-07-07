package org.mosip.ussd.dialog;

import java.io.BufferedReader;

import java.io.InputStream;
import java.io.InputStreamReader;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.mosip.ussd.model.Commands;

public final class UssdMenu {
    JSONObject jsonMenu;

	public static void test(){
		UssdMenu m = new UssdMenu();
		m.loadMenu("en");
		String ret = m.constructMenu("mainMenu", Commands.CON, true);
		System.out.println(ret);
		ret = m.constructMenu("residentServices", Commands.CON, true);
		System.out.println(ret);
		

	}
	public void loadMenu(String lang){
		if(lang == null || lang.equals(""))
			lang = "en";
		JSONParser parser = new JSONParser();
		try {
			String filePath = "/"+lang + "/menu.json";

			InputStream in = getClass().getResourceAsStream(filePath);
			if(in != null){
    			BufferedReader reader = new BufferedReader(new InputStreamReader(in));
				Object obj = parser.parse(reader);
				//File file = new File(getClass().getClassLoader().getResource(filePath).getFile());

		   		//Object obj = parser.parse(new FileReader(file));
		   		jsonMenu = (JSONObject)obj;
			}
			else
			throw(new Exception("menu.json not found"));

		}catch(Exception e){
			e.printStackTrace();
		}
	}
	public  String constructMenu(String menuName, Commands comnd, Boolean bIncludeCmd, String extraMenuStr) {
		
		return constructMenu(menuName, comnd,bIncludeCmd,new String[]{extraMenuStr});
	}
	public  String constructMenu(String menuName, Commands comnd, Boolean bIncludeCmd, String[] extraMenuItems) {
		String ret ="";
		
		String[] menuStr;
	
		menuStr = getMenu(menuName);
		if(bIncludeCmd)
			ret = comnd.name() +" ";
		for(String s: menuStr){
			if(s != null && !s.isEmpty())
				ret += s + "\n";
		}
		if(extraMenuItems != null){
			for(String m: extraMenuItems)
				ret += m +"\n";
		}
		
		return ret;

	}
	public  String constructMenu(String menuName, Commands comnd, Boolean bIncludeCmd) {
		String ret ="";
		
		String[] menuStr;
	
			menuStr = getMenu(menuName);
			if(bIncludeCmd)
				ret = comnd.name() +" ";
			for(String s: menuStr)
				ret += s + "\n";
		
		
		return ret;
	}
	String[] getMenu(String menuName) {
		if(jsonMenu.containsKey(menuName)){
			Object obj = jsonMenu.get(menuName);

			if(obj instanceof JSONArray){
				JSONArray menuItem = (JSONArray)obj;
				String []  strMenuItems = new String[  menuItem.size()];
	
				for (int i=0;  i < menuItem.size(); i++) {
					strMenuItems[i] = menuItem.get(i).toString();
				}
				return strMenuItems;
			}	
		}
		
		return new String[1];
	}
/* 
    public static String[] mainMenu = {
		"Enter VID/UIN"
	};
	public static String[] mainMenu_hin = {
		"वीआईडी/यूआईएन दर्ज करें"
	};
	public static String[] authenticateMenu = {
		"Enter OTP"
		
	};
	public static String[] errorMessage = {
			"Invalid Option"
	};
	public static String[] successMessage = {
		"Completed successfuly."	
	};
	public static String [] residentServices = {
		"1. Transfer Credentials to Relying Party",
		"2. Get Temporary VID",
		"3. Get Perpetual VID",
		"4. Get Last 5 Acitities"
	};
	public static String [] residentServices_hin = {
		"1. भरोसेमंद पार्टी को क्रेडेंशियल ट्रांसफर करें",
		"2. अस्थायी वीआईडी ​​प्राप्त करें"
	};

    public static String [] RPPartnerIdMenu = {
		"Enter Relying Party Partner-Id"
		
	};
    public static String [] RPApplMenu = {
		"Enter Application-Id"
		
	};
	public static String [] mapperMainMenu = {
		"Enter UIN"
	};
	*/
}
