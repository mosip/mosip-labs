package io.mosip.selfregistration.dto;

import lombok.*;

import javax.validation.constraints.Email;
import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.util.List;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SelfRegDto {

    private String rid;

    @NotNull(message = "Name cannot be blank")
    private List<SimpleType> fullName;

    @NotBlank(message = "DOB cannot be blank")
    private String dateOfBirth;

    @NotNull(message = "Gender cannot be blank")
    private List<SimpleType> gender;

    private String phone;

    @Email(message = "Invalid email format.")
    private String email;

    private List<SimpleType> address;

    @NotBlank(message = "Photo cannot be blank")
    private String photo;

    @NotBlank(message = "Preferred Language cannot be blank")
    private String preferredLang;

    @NotBlank(message = "Captcha required")
    private String captchaToken;

}
