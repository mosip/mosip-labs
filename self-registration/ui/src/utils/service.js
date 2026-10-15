import axios from "axios";

const API_BASE_URL =
  process.env.NODE_ENV === "development"
    ? process.env.REACT_APP_SELF_REGISTRATION_URL
    : window.origin + process.env.REACT_APP_SELF_REGISTRATION_URL;

console.log(process.env.REACT_APP_SELF_REGISTRATION_URL);
console.log(API_BASE_URL);

export const register = async (userData, setStatus, setUin) => {

  try {
    setStatus({ state: "loading", message: "loading" });

    const response = await axios.post(
      API_BASE_URL + "/create",
      userData,
      {
        headers: {
          "Content-Type": "application/json",
          
        },
      }
    );
    console.log("success");
    console.log("API Response:", response.data);
    if (response.status === 200) {
      if (response.data?.response?.status === "ACTIVATED") {
        setStatus({ state: "success", message: "Registration successful!" });
        setUin(response.data?.id); 
      } else if (response.data?.response === null) {
        if (response.data?.errors[0].errorCode === "SELF_ERR-001")
          setStatus({ state: "error", message: "SELF_ERR-001" });
        else if (response.data?.errors[0].errorCode === "SELF_ERR-002")
          setStatus({ state: "error", message: "SELF_ERR-002" });
        else setStatus({ state: "error", message: "SELF_ERR-003" });
      }
    } else {
      setStatus({ state: "error", message: "SELF_ERR-003"})
    }

  } catch (error) {
    console.error("Error:", error);
    let errorMessage = "SELF_ERR-003";

    if (error.response) {
      if (error.response.data?.errors[0].errorCode === "SELF_ERR-001")
        setStatus({ state: "error", message: "SELF_ERR-001" });
      else setStatus({ state: "error", message: "SELF_ERR-002" });
    } else setStatus({ state: "error", message: errorMessage });

    console.error("Error:", errorMessage);
  }
};
