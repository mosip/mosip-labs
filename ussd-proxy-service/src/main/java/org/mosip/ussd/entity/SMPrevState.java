package org.mosip.ussd.entity;
import javax.persistence.Id;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.GeneratedValue;
import javax.persistence.Table;

import org.hibernate.annotations.Immutable;
//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name="PrevStates")
@Getter
@Setter
@NoArgsConstructor
//@Immutable
//@RedisHash("SMPrevState")
public class SMPrevState {
    
    @Id
    @GeneratedValue
    private Long id;

    @Column(name="seqNo")
    private Long seqNo;

    @Column(name="sessionId")
    private String sessionId;
    @Column(name="prevStateName")
    private String prevStateName;
    

}
