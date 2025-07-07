package org.mosip.ussd.config;


import org.springframework.batch.core.Job;
import org.springframework.batch.core.configuration.annotation.EnableBatchProcessing;
import org.springframework.batch.core.configuration.annotation.JobBuilderFactory;
import org.springframework.batch.core.configuration.annotation.StepBuilderFactory;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.launch.support.SimpleJobLauncher;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.tasklet.TaskletStep;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.SimpleAsyncTaskExecutor;
import org.mosip.ussd.service.CredentialService;
import org.mosip.ussd.util.CredentialTask;
import org.mosip.ussd.util.CredentialsHelper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Configuration
@EnableBatchProcessing


public class CredentialJobConfig {
    @Autowired
    private JobBuilderFactory jobs;
   
    @Autowired
    private StepBuilderFactory steps;
    
    @Autowired
    JobRepository jobRepository;
    
    
    
    @Autowired
    CredentialService credentialService;

    private static final Logger logger = LoggerFactory.getLogger(CredentialsHelper.class);
  
    @Bean
    public TaskletStep stepOne(){
      return steps.get("stepOne")
              .tasklet(new CredentialTask(credentialService))
              .build();
    }

    @Bean(name ="simpleJobLauncher")
    public JobLauncher simpleJobLauncher() throws Exception {
        logger.info("simpleJobLauncher entry");

        SimpleJobLauncher jobLauncher = new SimpleJobLauncher();
        jobLauncher.setJobRepository(jobRepository);
        jobLauncher.setTaskExecutor(new SimpleAsyncTaskExecutor());
        jobLauncher.afterPropertiesSet();
        logger.info("simpleJobLauncher return");
        
        return jobLauncher;
    }
    @Bean
    public Job credentialJob(){
        return jobs.get("credentialJob")
            .incrementer(new RunIdIncrementer())
            .start(stepOne())
             //   .next(stepTwo())
            .build();
    }

}
