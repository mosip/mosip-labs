package org.mosip.ussd.entity;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.Table;

//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import javax.persistence.Id;
    
@Entity
@Table(name="SMVariables")
@Getter
@Setter
@NoArgsConstructor
//@RedisHash("SMVariables")
public class SMVariables {
    @Id
    @GeneratedValue
    private Long Id;

    @Column(name="sessionId")
    private String sessionId;

    @Column(name="key")
    private String key;
    @Column(name="value")
    private String value;
    
    
}
