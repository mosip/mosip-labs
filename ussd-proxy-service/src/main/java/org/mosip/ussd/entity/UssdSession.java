package org.mosip.ussd.entity;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import org.hibernate.annotations.Immutable;
//import org.springframework.data.redis.core.RedisHash;

import javax.persistence.CascadeType;
import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.FetchType;
import javax.persistence.Id;
import javax.persistence.OneToMany;
import javax.persistence.Table;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name="UssdSession")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
//@Immutable
//@RedisHash("UssdSession")
public class UssdSession {
    @Id
    private String id;
    
    @Column(name="phoneNo")
    private String phoneNo;  
   
    @OneToMany(fetch = FetchType.EAGER,mappedBy="ussdSession",cascade = CascadeType.ALL)
   // @OneToMany(mappedBy = "ussdSession" ,cascade = {CascadeType.ALL}, orphanRemoval = true)
   // @Fetch(FetchMode.SUBSELECT)
    private List<UssdSessionValue> values = new ArrayList<>();
   
    public UssdSession(String sessionId, String phoneNo){
        this.id = sessionId;
        this.phoneNo = phoneNo;
    }
    public UssdSessionValue findValue(String key){

        return values
        .stream()
        .filter(value -> key.equals(value.getKey()))
        .findAny()
        .orElse(null);

    }
    public void addValue(UssdSessionValue value){
        value.setUssdSession(this);
        values.add(value);
    }
    public UssdSessionValue updateValue(UssdSessionValue value){
        UssdSessionValue foundValue = null;
        foundValue = values
                        .stream()
                        .filter(v -> value.getKey().equals(v.getKey()))
                        .findAny()
                        .orElse(null);
        if(foundValue != null)
            foundValue.setValue(value.getValue());

/** 
        for(UssdSessionValue v: values){
            if(v.getKey().equals(value.getKey())){
                v.setValue(value.getValue());
                foundValue = v;
                break;
            }
        }   
**/
        return foundValue;
    }
}
