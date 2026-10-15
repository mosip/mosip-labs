import React, { useState, useRef } from "react";
import Preview from "./Preview";
import { ErrorPopup, PopupLoader, SuccessPopup } from "./Popup";
import camera_icon from "../assets/camera_icon.png";
import user_icon from "../assets/user_icon.png";
import { useTranslation } from "react-i18next";
import { register } from "../utils/service";
import ReCAPTCHA from "react-google-recaptcha";
import Compressor from "compressorjs";

const Register = () => {
  const [selectedImage, setSelectedImage] = useState(null);
  const [base64Image, setBase64Image] = useState(""); // State for Base64 image
  const [fullName, setFullName] = useState("");
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [email, setEmail] = useState("");
  const [gender, setGender] = useState("");
  const [address, setAddress] = useState("");
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState({});
  const [dateError, setDateError] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [showSuccessPopup, setShowSuccessPopup] = useState(false);
  const [status, setStatus] = useState({ state: "idle", message: "idle" }); // idle-success-error-loading
  const [captchaToken, setCaptchaToken] = useState(null);
  const [uin, setUin] = useState("");
  const _reCaptchaRef = useRef(null);

  const handleCaptchaChange = (value) => {
    setCaptchaToken(value);
    console.log("value", captchaToken);
    console.log("captchaToken", value);
  };
  const captchaSiteKey = "lllll";

  const fileInputRef = useRef(null);

  const { t } = useTranslation();

  const { i18n } = useTranslation();

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraOn, setCameraOn] = useState(false);

  const startCamera = async () => {
    if (selectedImage) {
      console.log("Photo already exists, cannot take another one.");
      return;
    }
    setErrors((prevErrors) => ({
      ...prevErrors,
      photo: "",
    }));
    setCameraOn(true);
    try {
      const constraints = {
        audio: false,
        video: {
          facingMode: "user", // Use "environment" for rear camera
        },
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.muted = true;
        videoRef.current.play();
      }
    } catch (error) {
      console.error("Error accessing camera:", error);
    }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject;
      const tracks = stream.getTracks(); // Ensure tracks exist before stopping
      tracks.forEach((track) => track.stop()); // Stop each track
      videoRef.current.srcObject = null; // Clear video source
    }

    // Update state after stopping the camera
    setCameraOn(false);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const context = canvasRef.current.getContext("2d");
      context.drawImage(
        videoRef.current,
        0,
        0,
        canvasRef.current.width,
        canvasRef.current.height
      );

      const imageData = canvasRef.current.toDataURL("image/jpeg", 0.5); // Convert to Base64

      console.log("Original data");
      console.log(canvasRef.current.toDataURL("image/jpeg"));

      console.log("compress data");
      console.log(imageData);


      setSelectedImage(imageData);
      setBase64Image(imageData);

      // Clear the photo error when capturing an image
      setErrors((prevErrors) => ({
        ...prevErrors,
        photo: "",
      }));

      stopCamera(); // Stop camera after capturing photo
    }
  };


  const blob2base64 = (blob, mimeType = "image/jpeg") => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrlPrefix = `data:${mimeType};base64,`;
        const base64WithDataUrlPrefix = reader.result;
        if (base64WithDataUrlPrefix !== null) {
          const base64 = base64WithDataUrlPrefix.replace(dataUrlPrefix, "");
          resolve(base64);
        }
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const base64ToBlob = async (base64) => {
    const response = await fetch(base64);
    const blob = await response.blob();
    return blob;
  };

  // const handleFileChange = (event) => {
  //   const file = event.target.files[0];
  //   if (file) {
  //     const allowedTypes = ["image/png", "image/jpeg", "image/jpg"];

  //     // Check file type
  //     if (!allowedTypes.includes(file.type)) {
  //       setErrors((prevErrors) => ({
  //         ...prevErrors,
  //         photo: "format_err",
  //       }));
  //       return;
  //     }

  //     // Check file size (5MB max)
  //     if (file.size > 5 * 1024 * 1024) {
  //       setErrors((prevErrors) => ({
  //         ...prevErrors,
  //         photo: "photo_err",
  //       }));
  //       return;
  //     }

  //     setErrors((prevErrors) => ({ ...prevErrors, photo: "" }));

  //     const imageUrl = URL.createObjectURL(file);
  //     setSelectedImage(imageUrl);

  //     console.log("************file change");

  //     console.log(imageUrl);

  //     // Convert file to Base64
  //     const reader = new FileReader();
  //     reader.onload = async () => {
  //       console.log("*********inside onload");

  //       console.log(reader.result);
  //       const blobData = await base64ToBlob(reader.result);

  //       console.log("********blob data");
  //       console.log(blobData);

  //       new Compressor(blobData, {
  //         quality: 0.3,
  //         async success(result) {
  //           console.log("**** inside success of compressor");
  //           console.log(result);
  //           const imageData = await blob2base64(result);
  //           console.log(imageData);

  //           setBase64Image(imageData);
  //         }
  //       })


  //       setBase64Image(reader.result);
  //     };
  //     reader.readAsDataURL(file);
  //   }
  // };

  // Function to trigger file input when div is clicked
  // const handleUploadClick = () => {
  //   fileInputRef.current.click();
  // };
  const handleDateChange = (e) => {
    const selectedDate = e.target.value;
    setDateOfBirth(selectedDate);

    const today = new Date();
    const minDate = new Date();
    minDate.setFullYear(today.getFullYear() - 5); // 5 years back

    if (new Date(selectedDate) > today) {
      setDateError("Date_Future_Error");
    } else if (new Date(selectedDate) > minDate) {
      setDateError("age_err");
    } else {
      setDateError(""); // Clear error if valid
    }
  };

  // Function to validate the form
  const validateForm = () => {
    const newErrors = {};

    // Name validation
    if (!fullName.trim()) {
      newErrors.fullName = "err_fn";
    }

    // Mobile number validation
    if (mobileNumber) {
      if (!/^\d+$/.test(mobileNumber)) {
        newErrors.mobileNumber = "err_mn_n";
      } else if (mobileNumber.length <= 9 || mobileNumber.length > 10) {
        newErrors.mobileNumber = "err_mn_digits";
      }
    }
    if (!dateOfBirth) {
      newErrors.dateOfBirth = "Date_Of_Birth_Required";
    } else if (new Date(dateOfBirth) > new Date()) {
      newErrors.dateOfBirth = "Date_Of_Birth_Future_Error";
    }

    if (!email.trim()) {
      newErrors.email = "err_eml";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "err_eml_inv";
    }

    if (!selectedImage) {
      newErrors.photo = "err_pht";
    }

    // Consent validation
    if (!consent) {
      newErrors.consent = "err_cnst";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Function to handle form submission for preview
  const handlePreview = () => {
    if (validateForm()) {
      setPreviewData({
        fullName,
        dateOfBirth,
        mobileNumber,
        email,
        gender,
        address,
        selectedImage,
      });
    }
  };

  // Function to clear the form
  const handleClear = () => {
    setFullName("");
    setDateOfBirth("");
    setMobileNumber("");
    setEmail("");
    setGender("");
    setAddress("");
    setSelectedImage(null);
    setConsent(false);
    setErrors({});
    setDateError("");
    setBase64Image("");
  };
  const deletePhoto = () => {
    setSelectedImage(null);
    setBase64Image(""); // Clear Base64 image
    if (fileInputRef.current) {
      fileInputRef.current.value = ""; // Reset file input
    }
  };

  // Function to handle submit button click
  const handleSubmit = async () => {
    if (!validateForm()) return; // Validate the form before submission

    // const newUIN = generateUIN(); // Generate a unique UIN
    // setUin(newUIN); // Set the UIN in state
    setShowSuccessPopup(true); // Show success popup
    setPreviewData(null); // Close the preview popup
    handleClear(); // Clear the form

    const langs = {
      en: "eng",
      es: "spa",
      fr: "fra",
    };
    // Prepare the userData object
    //   const [day, month, year] = dateOfBirth.split("/");
    // const formattedDateOfBirth = `${year}/${month}/${day}`;

    const userData = {
      fullName: [
        {
          language: langs[i18n.language],
          value: fullName,
        },
      ],
      preferredLang: langs[i18n.language],
      phone: `${mobileNumber}`,
      email: email,
      dateOfBirth: dateOfBirth.replace(/-/g, "/"),
      gender: [
        {
          language: langs[i18n.language],
          value: gender,
        },
      ],

      address: [
        {
          language: langs[i18n.language],
          value: address,
        },
      ],
      photo: base64Image, // Use the Base64 string here
      captchaToken: captchaToken,
    };
    // Send data to backend through API
    register(userData, setStatus, setUin);
  };

  return (
    <>
      {!previewData && !showSuccessPopup &&
        <div className="h-[100%] w-full bg-[#EFF3F8] flex items-center p-4 justify-center">
          <div className="-mt-[4rem] bg-white rounded-[1.3rem] shadow-lg w-full max-w-3xl p-8 lg:px-8">
            <h2 className="text-[1.3rem] md:text-[2.2rem] text-center font-semibold mb-2">
              {t("title")}
            </h2>
            <hr className="border-t border-gray-200 my-4" />
            <form className="flex flex-col md:flex-row gap-x-[10%]">
              <div className="mb-0 my-4 sm:gap-x-6 md:w-[50%]">
                <div className="">
                  <label className="block text-xs md:text-sm font-normal">
                    {t("name")}
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    className="p-2 w-full border rounded-md sm:mb-3 my-2 focus:outline-none  text-xs md:text-sm"
                    placeholder={t("Name_Placeholder")}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  {errors.fullName && (
                    <p className="text-red-500 text-sm sm:mb-3">
                      {errors.fullName}
                    </p>
                  )}
                </div>

                <div className="">
                  <label className="block text-xs md:text-sm font-normal">
                    {t("date_of_birth")}
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    className={`p-1 mb:p-2 w-full border rounded-md sm:mb-3 my-2  text-xs md:text-sm focus:outline-none uppercase ${!dateOfBirth && "text-[#A0A8AC]"}`}
                    placeholder="DD-MM-YYYY"
                    value={dateOfBirth}
                    max={new Date().toISOString().split("T")[0]} // Restrict future dates
                    onChange={handleDateChange}
                    onBlur={() => {
                      if (!dateOfBirth) {
                        setDateError("Valid_Date");
                      }
                    }}
                  />
                  {errors.dateOfBirth && (
                    <p className="text-red-500 text-sm sm:mb-3">
                      {errors.dateOfBirth}
                    </p>
                  )}
                  {dateError && (
                    <p className="text-red-500 text-sm sm:mb-3">{t(dateError)}</p>
                  )}
                </div>

                <div className="md:hidden">
                  <label className="block text-xs md:text-sm font-normal">{t("phone")}</label>
                  <input
                    type="text"
                    className="p-2 border w-full md:w-[15rem] rounded-md my-2 text-xs md:text-sm focus:outline-none"
                    placeholder={t("Mobile_Placeholder")}
                    value={mobileNumber}
                    onChange={(e) => {
                      // Allow only numbers
                      const numericValue = e.target.value.replace(/\D/g, ""); // Remove non-numeric characters
                      setMobileNumber(numericValue);

                      // Clear error when user starts typing
                      if (errors.mobileNumber) {
                        setErrors((prev) => ({ ...prev, mobileNumber: "" }));
                      }
                    }}
                    onBlur={(e) => {
                      // Validate on blur
                      const isValidLength =
                        e.target.value.length >= 9 && e.target.value.length <= 10;

                      if (!isValidLength) {
                        setErrors((prev) => ({
                          ...prev,
                          mobileNumber: "invalid_phone",
                        }));
                      }
                    }}
                  />
                  {errors.mobileNumber && (
                    <p className="text-red-500 text-sm sm:mb-3">
                      {t(errors.mobileNumber)}
                    </p>
                  )}
                </div>

                <div className="">
                  <label className="block text-xs md:text-sm font-normal">
                    {t("gender")}
                    <span className="text-red-500">*</span>
                  </label>{" "}
                  {/* Removed * */}
                  <select
                    className="p-2 w-full rounded-md sm:mb-3 my-2 text-xs md:text-sm border focus:outline-none"
                    value={gender}
                    onChange={(e) => {
                      const selectedValue = e.target.value;
                      if (selectedValue && selectedValue !== "") {
                        setGender(selectedValue);
                      }
                    }}
                    required
                  >
                    <option value="">{t("select")}</option>
                    <option>{t("male")}</option>
                    <option>{t("female")}</option>
                    <option>{t("other")}</option>
                  </select>
                </div>

                <div className="">
                  <label className="block text-xs md:text-sm font-normal">
                    {t("email")}
                    <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    className="p-2 w-full rounded-md sm:mb-3 my-2 border text-xs md:text-sm focus:outline-none"
                    placeholder={t("Email_Placeholder")}
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      // Clear error when user starts typing
                      if (errors.email) {
                        setErrors((prev) => ({ ...prev, email: "" }));
                      }
                    }}
                    onBlur={(e) => {
                      // Validate email on blur
                      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                      if (!emailRegex.test(e.target.value)) {
                        setErrors((prev) => ({
                          ...prev,
                          email: "invalid_email",
                        }));
                      }
                    }}
                  />
                  {errors.email && (
                    <p className="text-red-500 text-sm sm:mb-3">
                      {t(errors.email)}
                    </p>
                  )}
                </div>

                <div className="mb-4 sm:mt-0 mt-2">
                  <label className="block text-xs md:text-sm font-normal">{t("address")}</label>
                  <textarea
                    type="text"
                    className="w-full md:w-[21.5rem] border text-xs md:text-sm rounded p-2 mt-1 focus:outline-none"
                    placeholder={t("Address_Placeholder")}
                    value={address}
                    onChange={(e) => {
                      if (e.target.value.length <= 200) {
                        setAddress(e.target.value);
                      }
                    }}
                  />
                  <p className="text-gray-500 text-sm">{t(address.length)}/200</p>
                </div>
              </div>

              <div>
                <div className="flex flex-col md:w-[50%] md:mt-[6%]">

                  {/* Uploading photo section */}
                  <div className="">
                    <div className="flex flex-col">
                      <label className="block text-xs md:text-sm font-normal">
                        {t("photo")} <span className="text-red-500">*</span>
                      </label>
                      <div
                        className="flex flex-col border rounded-xl md:p-4 bg-[#FDFDFD] text-center items-center h-[10rem] w-full justify-center md:w-[230px] md:h-[155px]"
                      >
                        {selectedImage ? (
                          <div className="relative w-full h-full">
                            <img
                              src={selectedImage}
                              alt="Uploaded"
                              className="w-full h-full object-cover rounded-xl"
                            />
                            <button
                              className="absolute top-2 right-2 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center"
                              onClick={(e) => { e.stopPropagation(); deletePhoto(); }}
                            >
                              ×
                            </button>
                          </div>
                        ) : cameraOn ? (
                          <div className="relative w-full h-full">
                            <video
                              autoPlay
                              loop
                              muted
                              playsInline
                              ref={videoRef}
                              className="w-full h-full object-cover rounded-lg border"
                            ></video>
                          </div>
                        ) : (
                          <div
                            className="flex flex-col items-center"
                            // onClick={handleUploadClick}
                          >
                            <img src={user_icon} alt="user_icon" />
                          </div>
                        )}
                      </div>
                    </div>

                    {/* <input
                      type=""
                      accept="image/png, image/jpeg, image/jpg, .pdf, .txt"
                      ref={fileInputRef}
                      className="hidden"
                      onChange={handleFileChange}
                    /> */}
                    {errors.photo && (
                      <p className="text-red-500 text-sm sm:mb-3">
                        {t(errors.photo)}
                      </p>
                    )}
                    {cameraOn ? (
                      <button
                        type="button"
                        onClick={capturePhoto}
                        className="flex justify-center bg-green-600 max-sm:mb-2 text-xs md:text-sm font-[500] text-white md:w-[15rem] w-full py-2 rounded-md md:rounded-lg my-4"
                      >
                        {t("take_photo")}
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={startCamera}
                        className="flex items-center justify-center gap-x-3 bg-[#1763AC] max-sm:mb-2 text-xs md:text-sm font-[500] text-white md:w-[15rem] w-full py-2 rounded-md md:rounded-lg my-4"
                      >
                        <img src={camera_icon} />
                        {t("take_photo")}
                      </button>
                    )}
                  </div>
                  {/* Uploading photo section */}

                  <div className="hidden md:block">
                    <label className="block text-xs md:text-sm font-normal">{t("phone")}</label>
                    <input
                      type="text"
                      className="p-2 border w-full md:w-[15rem] rounded-md my-2 text-xs md:text-sm focus:outline-none"
                      placeholder={t("Mobile_Placeholder")}
                      value={mobileNumber}
                      onChange={(e) => {
                        // Allow only numbers
                        const numericValue = e.target.value.replace(/\D/g, ""); // Remove non-numeric characters
                        setMobileNumber(numericValue);

                        // Clear error when user starts typing
                        if (errors.mobileNumber) {
                          setErrors((prev) => ({ ...prev, mobileNumber: "" }));
                        }
                      }}
                      onBlur={(e) => {
                        // Validate on blur
                        const isValidLength =
                          e.target.value.length >= 9 && e.target.value.length <= 10;

                        if (!isValidLength) {
                          setErrors((prev) => ({
                            ...prev,
                            mobileNumber: "invalid_phone",
                          }));
                        }
                      }}
                    />
                    {errors.mobileNumber && (
                      <p className="text-red-500 text-sm sm:mb-3">
                        {t(errors.mobileNumber)}
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <canvas
                ref={canvasRef}
                className="hidden"
                width={320}
                height={240}
              ></canvas>
            </form>

            <div className="mt-6 text-[9.5px] md:text-base ">
              <p className="pt-4">{t("details")}</p>
              <div className="flex justify-start items-center mt-4">
                {" "}
                <input
                  type="checkbox"
                  className="size-3 md:size-4"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                />
                <p className="ml-2 text-xs md:text-sm">{t("consent")}</p>
                <span className="text-red-500">*</span>
              </div>
              {errors.consent && (
                <p className="text-red-500 text-sm">{t(errors.consent)}</p>
              )}
            </div>
            <div className="my-6">
              <div className="flex justify-center">
                <ReCAPTCHA
                  key={i18n.language} // Re-render on language change
                  hl={i18n.language}
                  ref={_reCaptchaRef}
                  onChange={handleCaptchaChange}
                  sitekey={window._env_?.RECAPTCHA_SITE_KEY || "fallback-site-key"}
                />
              </div>
              {errors.captcha && (
                <p className="text-red-500 text-sm text-center mt-2">
                  {t(errors.captcha)}
                </p>
              )}
            </div>
            <hr className="border-t border-gray-200 my-4" />
            <div className="flex flex-col items-center space-y-3 md:justify-end md:flex-row mt-6 md:space-x-4 ">
              <button
                className="border w-full py-1.5 md:mt-3 md:w-[25%] text-sm font-[500] rounded-[0.4rem] md:rounded-md border-[#1763AC] text-[#1763AC] cursor-pointer hover:text-white hover:bg-[#1763AC]"
                onClick={handleClear}
              >
                {t("clear_form")}
              </button>
              <button
                className={`bg-[#1763AC] text-sm text-white w-full md:w-[25%] py-1.5 rounded-[0.4rem] md:rounded-md ${!(
                  fullName &&
                  dateOfBirth &&
                  email &&
                  selectedImage &&
                  consent &&
                  gender &&
                  captchaToken
                )
                  ? "opacity-50 cursor-not-allowed"
                  : ""
                  }`}
                disabled={
                  !(
                    fullName &&
                    dateOfBirth &&
                    email &&
                    selectedImage &&
                    consent &&
                    gender && 
                    captchaToken
                  )
                }
                onClick={handlePreview}
              >
                {t("preview")}
              </button>
            </div>
          </div >
        </div >
      }

      {/* Preview Popup */}
      {
        previewData && (
          <Preview
            handleSubmit={handleSubmit}
            setPreviewData={setPreviewData}
            previewData={previewData}
          />
        )
      }

      {/* Success Popup */}
      {
        showSuccessPopup &&
        (status.state === "success" ? (
          <SuccessPopup uin={uin} setShowSuccessPopup={setShowSuccessPopup} />
        ) : status.state === "error" ? (
          <ErrorPopup
            message={status.message}
            setShowSuccessPopup={setShowSuccessPopup}
          />
        ) : status.state === "loading" ? (
          <PopupLoader message={t(status.message)} />
        ) : null)
      }
    </>

  );
};

export default Register;
