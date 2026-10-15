package io.mosip.selfregistration.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * Instantiates a new json value.
 */
@AllArgsConstructor
@NoArgsConstructor
@Data
public class SimpleType implements Serializable {

	/** The language. */
	private String language;
	
	/** The value. */
	private String value;
}
