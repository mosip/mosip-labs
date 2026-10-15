import { useTranslation } from "react-i18next";
import { RxCheck, RxCross2 } from "react-icons/rx";
import { TbLoader2 } from "react-icons/tb";

const SuccessPopup = ({ setShowSuccessPopup, uin }) => { 
  const { t } = useTranslation();
  return (
    <div className="bg-[#EFF3F8] inset-0 flex items-center justify-center">
      <div className="bg-white -mt-[4rem] md:-mt-[2.3%] mb-[5%] rounded-xl p-6 md:p-8 lg:px-12 w-[95%] md:w-full max-w-lg text-center border border-t-4 border-t-green-600 shadow">
        {/* Right Symbol (✓) */}
        <div className="flex justify-center items-center mb-4">
          <div className="w-20 h-20 md:w-24 md:h-24 bg-[#0A87541A] rounded-full flex items-center justify-center">
            <span className="text-green-600 text-4xl">
              <RxCheck />
            </span>
          </div>
        </div>

        <h2 className="text-xl md:text-3xl font-bold mt-8 mb-4">{t("congrats")}</h2>
        <p className="text-xs md:text-sm text-gray-600 mb-6 md:mb-12 ">
          {t("uin_message")}
          <span className="text-black-600 font-semibold"> {uin}</span>
          <br />
          {t("further_details")}
        </p>
        <hr className="h-1 border-gray-200 my-4" />
        <button
          className="text-white py-2  text-xs md:text-sm rounded-lg bg-[#0A8754] w-full md:w-[84%]"
          onClick={() => setShowSuccessPopup(false)}
        >
          {t("okay")}
        </button>
      </div>
    </div>
  );
};
const ErrorPopup = ({ setShowSuccessPopup, message }) => {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 bg-[#0B1E48] bg-opacity-90 flex items-center justify-center">
      <div className="bg-white rounded-xl p-8 lg:px-12 w-full max-w-md text-center border-rose-600 border-t-4">
        {/* Cross Symbol (X) */}
        <div className="flex justify-center items-center mb-4">
          <div className="w-24 h-24 bg-red-100 rounded-full flex items-center justify-center">
            <span className="text-rose-600 text-5xl">
              <RxCross2 />
            </span>
          </div>
        </div>

        <h2 className="text-3xl font-bold mt-6 mb-4">{t("error")}</h2>
        <p className="text-gray-600 mb-6 ">
          {/* {t("err_msg")} */}
          {message === "SELF_ERR-001"
            ? t("SELF_ERR-001")
            : message === "SELF_ERR-002"
            ? t("SELF_ERR-002")
            : t("SELF_ERR-003")}
        </p>
        <hr className="border-t border-gray-200 my-4" />
        <button
          className="bg-rose-700 text-white px-6 py-2 rounded-lg hover:bg-rose-800 w-full"
          onClick={() => setShowSuccessPopup(false)}
        >
          {t("okay")}
        </button>
      </div>
    </div>
  );
};
const PopupLoader = ({message}) => {
  return (
    <div className="fixed inset-0 bg-[#0B1E48] bg-opacity-90 flex items-center justify-center">
      <div className="bg-white flex flex-col items-center justify-center rounded-xl p-8 md:w-full max-w-md text-center border-t-4">
        <TbLoader2 className="size-6 animate-spin text-gray-600 " />
        <div className="flex items-center justify-center">
          {message}
        </div>
      </div>
    </div>
  );
};

export { PopupLoader, SuccessPopup, ErrorPopup };
