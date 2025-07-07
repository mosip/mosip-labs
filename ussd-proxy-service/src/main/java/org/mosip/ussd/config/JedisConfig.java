package org.mosip.ussd.config;
/* 
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.jedis.JedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;

@Configuration
public class JedisConfig {
  //@Value("${mosip.ussd.redis.connection-string}")
  //String redis_connection_string;
  
  @Value("${mosip.ussd.redis.connection.host}")
  String redis_connection_host;

  @Value("${mosip.ussd.redis.connection.port}")
  int redis_connection_port;

  @Value("${mosip.ussd.redis.connection.password}")
  String redis_connection_password;


    @Bean
    JedisConnectionFactory jedisConnectionFactory() {
        JedisConnectionFactory jedisConnectionFactory = null;

      RedisStandaloneConfiguration redisStandaloneConfiguration = new RedisStandaloneConfiguration(redis_connection_host);
      redisStandaloneConfiguration.setPort(redis_connection_port);
      redisStandaloneConfiguration.setPassword(redis_connection_password);
      
      jedisConnectionFactory = new JedisConnectionFactory(redisStandaloneConfiguration);
      jedisConnectionFactory.getPoolConfig().setMaxTotal(50);
      jedisConnectionFactory.getPoolConfig().setMaxIdle(50);

            
        return jedisConnectionFactory;
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate() {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(jedisConnectionFactory());
        return template;
    }
}
*/