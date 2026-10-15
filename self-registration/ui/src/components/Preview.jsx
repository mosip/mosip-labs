import { useTranslation } from "react-i18next";

const Preview = ({ previewData, handleSubmit, setPreviewData }) => {
  const { t } = useTranslation();
  return (
    <div className="bg-[#EFF3F8] inset-0 flex items-center justify-center">
      <div className="bg-white -mt-[5rem] md:-mt-[3%] rounded-xl p-3 md:p-8 lg:px-6 w-[90%] md:w-full max-w-xl border shadow mb-[7%]">
        <h2 className="place-self-center text-xl md:text-2xl text-gray-600 font-semibold mb-6 md:text-start md:ml-4 ">
          {t("confirm")}
        </h2>
        <hr className="border-t border-gray-200 my-2" />
        <div className="flex flex-row md:flex-row md:gap-6 md:px-4">
          {/* Left Column for Details */}
          <div className="flex-1 space-y-4">
            <div>
              <label className="block text-xs md:text-medium font-[400] text-[#666666]">
                {t("name")}
              </label>
              <p className="mt-1 text-sm md:text-lg font-semibold">
                {previewData.fullName}
              </p>
            </div>
            <div>
              <label className="block text-xs md:text-medium font-[400] text-[#666666]">
                {t("date_of_birth")}
              </label>
              <p className="mt-1 text-sm md:text-lg font-semibold">
                {previewData.dateOfBirth}
              </p>
            </div>
            <div>
              <label className="block text-xs md:text-medium font-[400] text-[#666666]">
                {t("gender")}
              </label>
              <p className="mt-1 text-sm md:text-lg font-semibold">{previewData.gender}</p>
            </div>
            <div>
              <label className="block text-xs md:text-medium font-[400] text-[#666666]">
                {t("email")}
              </label>
              <p className="mt-1 text-sm md:text-lg font-semibold w-32 md:w-full break-words">{previewData.email}</p>
            </div>
          </div>

          {/* Right Column for Photo and Mobile Number */}
          <div className="flex-1 ml-4 space-y-2">
            <label className="block text-xs md:text-medium font-[400] text-[#666666]">
              {t("photo")}
            </label>
            <div className="h-[48%] w-[87%] md:w-[63%] md:h-[63%] rounded-lg overflow-hidden">
              {previewData.selectedImage && (
                <img
                  src={previewData.selectedImage}
                  alt="Uploaded"
                  className="w- h-full object-cover border-4"
                />
              )}
            </div>
            <div>
              <label className="block text-xs md:text-medium font-[400] text-[#666666]">
                {t("phone")}
              </label>
              <p className="mt-1 text-sm md:text-lg font-semibold">
                {previewData.mobileNumber}
              </p>
            </div>
          </div>
          {/* Address box */}
        </div>
        <div className="md:px-4 break-words w-full">
          <label className="block text-xs md:text-medium font-[400] text-[#666666]">
            {t("address")}
          </label>
          <p className="mt-1 text-sm md:text-lg font-semibold">{previewData.address}</p>
        </div>
        <hr className="border-t border-gray-200 my-2" />

        {/* Buttons */}
        <div className="flex flex-col md:flex-row md:justify-end mt-6 md:mt-8 space-y-2 md:space-x-4">
          <div></div>
          <button
            className="text-[#1763AC]  border border-[#1763AC] text-xs md:text-sm w-full md:w-[30%] py-1.5 rounded-md md:rounded-lg"
            onClick={() => setPreviewData(null)}
          >
            {t("cancel")}
          </button>
          <button
            className="bg-[#1763AC] text-white  w-full md:w-[30%] text-xs md:text-sm py-1.5 rounded-md md:rounded-lg hover:bg-blue-700"
            onClick={handleSubmit}
          >
            {t("register")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Preview;
