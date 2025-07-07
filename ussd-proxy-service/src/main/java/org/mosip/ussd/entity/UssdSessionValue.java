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

import javax.persistence.GeneratedValue;
import javax.persistence.GenerationType;
import javax.persistence.Id;
import javax.persistence.JoinColumn;
import javax.persistence.ManyToOne;
import javax.persistence.Table;

@Entity
@Table(name="UssdSessionValues")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
//@Immutable
//@RedisHash("UssdSessionValue")
public class UssdSessionValue {
    
    @Id
    @GeneratedValue(strategy = GenerationType.AUTO)
    private Long id;

   //@ManyToOne(fetch = FetchType.LAZY)
   @ManyToOne(cascade= CascadeType.ALL)
   @JoinColumn(name = "sessionId")
   private UssdSession ussdSession;
    //private String sessionId;
    @Column(name="value")
    private String value;
    @Column(name="key")
    private String key;

    public UssdSessionValue(String sessionId, String key, String value){
   //     this.sessionId = sessionId;
        this.key = key;
        this.value = value;
    }
    public String toString(){
        StringBuffer buffer = new StringBuffer();
        buffer.append("\nsessionId="+  ussdSession.getId());
        buffer.append("\nId="+  getId());
        buffer.append("\nkey="+  getKey());
        buffer.append("\nvalue="+  getValue());
        return buffer.toString();
        
        
    }
}
