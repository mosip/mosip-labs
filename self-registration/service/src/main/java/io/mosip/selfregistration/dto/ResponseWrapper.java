package io.mosip.selfregistration.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class ResponseWrapper<T> {

    private String responseTime;
    private T response;
    private List<ErrorDTO> errors = new ArrayList<>();
}
