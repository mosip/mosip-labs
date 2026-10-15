package io.mosip.selfregistration;

import io.mosip.kernel.dataaccess.hibernate.config.HibernateDaoConfig;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration;
import org.springframework.boot.autoconfigure.security.servlet.SecurityAutoConfiguration;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication(scanBasePackages = {"io.mosip.selfregistration.*", "io.mosip.kernel.*"},
exclude = {SecurityAutoConfiguration.class, HibernateJpaAutoConfiguration.class})
@EnableAsync
public class SelfRegistrationApplication {

    public static void main(String[] args) {
        SpringApplication.run(SelfRegistrationApplication.class, args);
    }
}
