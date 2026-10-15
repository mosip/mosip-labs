import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import mosip_logo from "../assets/mosip_logo.png";
import hamburger_icon from "../assets/hanburger_icon.png";
import dropdown_icon from "../assets/DropDown_Icon.png";
import link_url_Icon from "../assets/link_url_Icon.png";
import link_line_icon from "../assets/link_line_Icon.png"
import { VscGlobe } from "react-icons/vsc";
import LanguageSelector from "./Language-selector";

const Banner = () => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false); // State to manage dropdown visibility
  const [hamburgerBtn, setHamburgerBtn] = useState(false);
  const [showDocumentMenu, setShowDocumentMenu] = useState(false);
  const [showAboutMenu, setShowAboutMenu] = useState(false);
  const { i18n } = useTranslation();
  const { t } = useTranslation();


  const languages = {
    en: "English",
    fr: "Français",
    es: "Spanish",
    ar: "Arabic",
  };
  return (
    <div className="flex flex-col justify-around left-0 w-full bg-banner_bg shadow-md h-auto py-6 px-[4%]">
      {/* MOSIP Logo on the left */}
      <div className="flex items-start justify-between">
        <div className="flex flex-col items-center space-x-3">
          <div className="flex items-center space-x-3">
            <img  src={hamburger_icon} className="lg:hidden h-3 w-4 cursor-pointer" onClick={() => setHamburgerBtn(!hamburgerBtn)} />
            <img
              src={mosip_logo}
              alt="MOSIP Logo"
              className="h-8 md:h-14" // Adjust height as needed
            />
          </div>
          {/* Hamburger button menu */}
          <div id="hamburgerDetails" className={`top-12 md:top-16 left-0 bg-[#012F5A] p-5 lg:hidden absolute text-[#2c2020] ${hamburgerBtn ? "block" : "hidden"}`}>
            <div className="group">
              <span className="flex items-center space-x-1 pb-2" onClick={() => setShowAboutMenu(!showAboutMenu)}>
                <span className="font-semibold text-[12px] text-white border-b border-[#ffffff]">{t('aboutMosip')}</span>
                <img src={dropdown_icon} className={`h-1 w-2 ${showAboutMenu && 'rotate-180'} duration-700`} alt="dropDown" />
              </span>
              <div className={`${showAboutMenu ?'block' : 'hidden'}`}>
                <a href="https://mosip.io/" target="_blank"
                  className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                  <span className="border-b border-[#ffffff]">{t('mosipWebsite')}</span>
                  <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                </a>

                <div className="block pl-5 py-1 text-[#ffffff] text-[10px]">
                  <span className="border-b border-[#ffffff]">{t('documentation')}</span>
                  <a href="https://docs.mosip.io/1.1.5" target="_blank"
                    className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                    <span className="border-b border-[#ffffff]">{t('doc1.1.5')} </span>
                    <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                  <a href="https://docs.mosip.io/1.2.0" target="_blank"
                    className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                    <span className="border-b border-[#ffffff]">{t('docs1.2.0')}</span>
                    <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                  <a href="https://docs.inji.io/" target="_blank"
                    className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                    <span className="border-b border-[#ffffff]">{t('inji')}</span>
                    <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                  <a href="https://docs.esignet.io/" target="_blank"
                    className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                    <span className="border-b border-[#ffffff]">{t('eSignet')}</span>
                    <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                </div>
                <a href="https://www.youtube.com/@mosip16" target="_blank"
                  className="flex pl-5 py-1 text-[#ffffff] text-[10px] items-center space-x-2">
                  <span className="border-b border-[#ffffff]">{t('youtubeVideos')}</span>
                  <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
                </a>
              </div>
            </div>
            <a href="https://community.mosip.io/" target="_blank"
              className="flex py-1 text-[#ffffff] text-[12px] items-center space-x-2 font-semibold mb-2">
              <span className="border-b border-[#ffffff]">{t('contactUs')}</span>
              <img src={link_url_Icon} className="h-3 w-3" alt="link_line_icon" />
            </a>
            <a href="https://mosip.stoplight.io/" target="_blank"
              className="block py-1 text-[#ffffff] text-[12px] items-center space-x-2 font-semibold mb-2">
              <span className="border-b border-[#ffffff]">{t('apis')}</span>
            </a>
          </div>
        </div>
        {/* Hamburger button menu */}


        <div className="flex items-center">
          <div className="lg:flex space-x-6 pt-3 hidden">
            <div className="group relative flex flex-col">
              <div className="group text-[#ffffff] flex items-center gap-x-2 cursor-pointer">
                <span className="group-hover:border-b text-[18px] text-white">{t('aboutMosip')}</span>
                <img src={dropdown_icon} className="h-1 w-2 group-hover:rotate-180 duration-700" alt="dropDown" />
              </div>
              <div id="dropdownCard"
                className="absolute hidden top-7 mt-[6px] w-[174px] -ml-10 bg-white rounded-md shadow-lg  z-50 group-hover:block duration-700">
                <div className="p-2">
                  <a href="https://mosip.io/" target="_blank"
                    className="flex justify-between hover:bg-gray-200 px-2 py-2 text-[#3E3E3E] border-b border-[#C4D6E6] text-[14px] items-center space-x-1 font-[500]">
                    <span>{t('mosipWebsite')}</span>
                    <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                  <div id="docLinkCard"
                    className="px-2 py-2 text-[#3E3E3E] border-b border-[#C4D6E6] text-[14px] flex items-center hover:bg-gray-200 font-[500] cursor-pointer" onMouseOver={() => setShowDocumentMenu(true)} onMouseOut={() => setShowDocumentMenu(false)}>
                    <span>{t('documentation')}</span>

                    {/* Docs version card */}
                    <div id="docVersiondropDown"
                      className={`absolute mt-32 w-[174px] ml-40 bg-white rounded-md shadow-lg duration-700 z-50 ${showDocumentMenu ? 'block' : 'hidden'}`}>
                      <div className="p-2">
                        <a href="https://docs.mosip.io/1.1.5" target="_blank"
                          className="flex justify-between px-2 py-2 text-[#3E3E3E] hover:bg-gray-200 border-b border-[#C4D6E6] text-[14px] items-center space-x-1 font-[500]">
                          <span>{t('doc1.1.5')}</span>
                          <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                        </a>
                        <a href="https://docs.mosip.io/1.2.0" target="_blank"
                          className="flex justify-between px-2 py-2 text-[#3E3E3E] hover:bg-gray-200 border-b border-[#C4D6E6] text-[14px] items-center space-x-1 font-[500]">
                          <span>{t('docs1.2.0')}</span>
                          <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                        </a>
                        <a href="https://docs.inji.io/" target="_blank"
                          className="flex justify-between px-2 py-2 text-[#3E3E3E] hover:bg-gray-200 border-b border-[#C4D6E6] text-[14px] items-center space-x-1 font-[500]">
                          <span>{t('inji')}</span>
                          <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                        </a>
                        <a href="https://docs.esignet.io/" target="_blank"
                          className="flex justify-between px-2 py-2 text-[#3E3E3E] hover:bg-gray-200 text-[14px] items-center space-x-1 font-[500]">
                          <span>{t('eSignet')}</span>
                          <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                        </a>
                      </div>
                    </div>

                  </div>
                  <a href="https://www.youtube.com/@mosip16" target="_blank"
                    className="px-2 py-2 justify-between hover:bg-gray-200 text-[#3E3E3E] text-[14px] flex items-center space-x-1 font-[500]">
                    <span>{t('youtubeVideos')}</span>
                    <img src={link_line_icon} className="h-3 w-3" alt="link_line_icon" />
                  </a>
                </div>
              </div>
            </div>
            <a href="https://community.mosip.io/" className="flex items-center space-x-2 cursor-pointer">
              <span className="hover:border-b text-[18px] text-white">{t('contactUs')}</span>
              <img src={link_url_Icon} className="h-4 w-4" alt="link_url_Icon" />
            </a>
            <a href="https://mosip.stoplight.io/" className="flex items-center space-x-2 cursor-pointer">
              <span className="hover:border-b text-[18px] text-white">{t('apis')}</span>
            </a>

            {/* Language Dropdown on the right */}
          </div>

          {/* Language Selector */}
          {/* <div className="relative"
            onClick={() => setIsDropdownOpen((prev) => !prev)}
            onBlur={(e) => {
              // Close dropdown if the focus is not moved to an element inside the dropdown
              if (!e.currentTarget.contains(e.relatedTarget)) {
                setIsDropdownOpen(false);
              }
            }}
            tabIndex={-1}
          // Open dropdown on hover
          >
            <button className="flex mt-1 md:mt-3 ml-5 items-center text-blue-700 text-xs md:text-base hover:text-blue-600 focus:outline-none">
              <VscGlobe
                data-testid="Language-Selector-Icon font-semibold"
                size={24}
                color={"white"}
              />
              <span
                className="ml-2 text-black-600 font-semibold"
                style={{ color: "white" }}
              >
                {languages[i18n.language]}
              </span>
              <img src={dropdown_icon} className={`h-1 w-2 mx-1 ${isDropdownOpen && 'rotate-180'} duration-700`} alt="dropDown" />
            </button>

            {isDropdownOpen && <LanguageSelector />}
          </div> */}
        </div>
      </div>

      <div className="self-center text-center pt-[2rem] pb-[6rem] space-y-6">
        <h1 className="text-white font-bold text-[1.5rem] md:text-[2.5rem] mt-6">{t('registerNow')}<br className="sm:hidden" />{t('getYourUin')}</h1>
        <h2 className="text-white font-[300] text-[1.25rem] mt-1">{t('subTitle')}</h2>
      </div>
    </div>
  );
};

export default Banner;
