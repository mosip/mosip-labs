package org.mosip.ussd.entity;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
import org.hibernate.annotations.Immutable;
//import org.springframework.data.redis.core.RedisHash;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name="smcontext")
@Getter
@Setter
@NoArgsConstructor
//@Immutable
//@RedisHash("StateMachineContext")
public class StateMachineContext {

    @Id
    @Column(name="Id")
    private String Id;
    @Column(name="currTransitionId")
    String currentTransitionId;
    @Column(name="prevTransitionId")
    String prevTransitionId;
    @Column(name="currStateName")
    String currentStateName;

}

