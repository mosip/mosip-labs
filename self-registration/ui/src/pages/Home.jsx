import Banner from "../components/BannerSection";
import Register from "../components/Register";
import { useTranslation } from "react-i18next";

const Home = () => {
  const { t } = useTranslation();

  return (
    <div>
      <Banner />
      {/* Your registration form */}
      <Register />
      {/* Footer */}
      <div className="h-[45px] bg-white flex items-center justify-center">
        <p className="text-[#727272] text-[10px] md:text-[16px]">{t('footerMsg')}</p>
      </div>
    </div>
  );
};
export default Home;
