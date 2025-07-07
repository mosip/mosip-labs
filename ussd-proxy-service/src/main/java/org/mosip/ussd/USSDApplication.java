package org.mosip.ussd;


import org.springframework.boot.autoconfigure.SpringBootApplication;

import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;


@SpringBootApplication
//@EnableJpaRepositories("org.mosip.*") 
//@ComponentScan(basePackages = { "org.mosip.*" })
//@EntityScan("org.mosip.*")
public class USSDApplication extends SpringBootServletInitializer {

	public static void main(String[] args) {
	
		new SpringApplicationBuilder(USSDApplication.class).build().run(args);
	}
	
		
}