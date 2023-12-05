<template>
  <div :class="`font-${lang}`">
    <div
        class="navbar bg-base-100 h-16 flex items-center justify-center drop-shadow-sm top-0 bg-opacity-80 backdrop-blur px-4 fixed">
      <!-- Left Side -->
      <div class="flex-1 px-2 lg:flex-none space-x-2">
        <img src="/src/assets/logo.png" alt="Joseon Space Logo" class="h-6 w-auto">
        <p class="text-md font-bold">{{ langData.title }}</p>
      </div>

      <!-- Right Side -->
      <div class="flex justify-end flex-1 px-0">

        <!-- Theme Controller -->
        <div class="tooltip tooltip-bottom" v-bind:data-tip="langData.theme_tooltip">
          <div class="btn btn-ghost ">
            <label class="swap swap-rotate">
              <!-- this hidden checkbox controls the state -->
              <input type="checkbox" class="theme-controller" v-model="isDarkTheme"/>
              <sun-icon class="swap-on fill-current h-5 w-auto"/>
              <moon-icon class="swap-off fill-current h-5 w-auto"/>
            </label>
          </div>
        </div>
        <!-- Language Controller -->
        <div class="flex items-stretch">
          <div class="dropdown dropdown-hover dropdown-end">
            <div class="btn btn-ghost">
              <LanguageIcon class="h-5 w-auto"/>
              <img class="h-4 w-auto" alt="Flag" :src="`/src/assets/lang-icon/${lang}.svg`">
              <ChevronDownIcon class="h-3 w-3 fill-current opacity-60 inline-block"/>
            </div>
            <ul tabindex="0" class="dropdown-content z-[1] menu p-2 shadow bg-base-200 rounded-box w-36">
              <li><p @click="changeLanguage('ko')"><img class="h-4 w-auto" src="/src/assets/lang-icon/ko.svg"
                                                        alt="Flag of South Korea">한국어</p></li>
              <li><p @click="changeLanguage('en')"><img class="h-4 w-auto" src="/src/assets/lang-icon/en.svg"
                                                        alt="Flag of USA">English
              </p>
              </li>
              <li><p @click="changeLanguage('es')"><img class="h-4 w-auto" src="/src/assets/lang-icon/es.svg"
                                                        alt="Flag of Spain">Español</p>
              </li>
              <li><p @click="changeLanguage('zh')"><img class="h-4 w-auto" src="/src/assets/lang-icon/zh.svg"
                                                        alt="Flag of China">中文</p>
              </li>
              <li><p @click="changeLanguage('ja')"><img class="h-4 w-auto" src="/src/assets/lang-icon/ja.svg"
                                                        alt="Flag of Japan">日本語</p>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!--  Hero  -->
    <div class="hero min-h-screen" style="background-image: url('/src/assets/hero-image.jpg')">
      <div class="hero-overlay bg-opacity-60"></div>
      <div class="max-w-xl w-full">
        <input type="text" placeholder="Search" class="input w-full"/>
      </div>
    </div>

    <!--  Main Content Feed-->
    <div class="flex items-center justify-center">
      <div class="flex-1 max-w-lg justify">
        <div v-for="article in articles" class="border border-base-300 bg-base-100 p-5">
          <h1 class="font-bold text-lg pb-2 truncate">{{ article.title }}</h1>
          <article class="prose">
            <div v-html="markdown.render(article.content)"></div>
          </article>
        </div>
      </div>
    </div>


  </div>

</template>


<script setup>
import {LanguageIcon, ChevronDownIcon, SunIcon, MoonIcon} from '@heroicons/vue/24/solid'
import {onMounted, reactive, ref, watch} from 'vue'
import {themeChange} from 'theme-change'
import axios from 'axios'
import MarkdownIt from "markdown-it";

const markdown = new MarkdownIt();
const apiOrigin = "http://127.0.0.1:8000/"

// ========== Language Management ==========
// Ref to store the current language
const lang = ref('en');

// Reactive dictionary for language data
const langData = reactive({
  title: "Joseon's Gung",
  theme_tooltip: "Toggle light/dark theme",
});

// Function to detect browser language
const detectBrowserLanguage = () => {
  const browserLang = navigator.language || navigator.userLanguage;
  if (browserLang) {
    if (browserLang.startsWith('es')) {
      lang.value = 'es';
    } else if (browserLang.startsWith('zh')) {
      lang.value = 'zh';
    } else if (browserLang.startsWith('ja')) {
      lang.value = 'ja';
    } else if (browserLang.startsWith('ko')) {
      lang.value = 'ko';
    } else {
      lang.value = 'en';
    }
  }
}

// Function to fetch language configuration
const fetchLanguageConfig = async () => {
  try {
    const response = await axios.get(apiOrigin + "api/v1/languages/", {params: {language: lang.value}});
    const responseData = JSON.parse(response.data[0]); // Parse the JSON string
    console.log("Parsed data:", responseData);
    Object.assign(langData, responseData);
  } catch (error) {
    console.error("Error fetching language config:", error);
  }
}

// Function to save language to local storage
const saveLanguageToLocalStorage = (language) => {
  localStorage.setItem('userLanguage', language);
}

// On mounted
onMounted(() => {
  const storedLang = localStorage.getItem('userLanguage');
  if (storedLang) {
    lang.value = storedLang;
  } else {
    detectBrowserLanguage();
  }
  fetchLanguageConfig();
});


const changeLanguage = (newLang) => {
  lang.value = newLang;
  fetchLanguageConfig();
  saveLanguageToLocalStorage(newLang);

  // Clear the articles array and fetch new feed
  articles.value = [];
  fetchFeed();
}

// ========== Theme Management ==========
const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const isDarkTheme = ref(prefersDark);
watch(isDarkTheme, (newValue) => {
  document.documentElement.setAttribute('data-theme', newValue ? 'dark' : 'light');
});
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
  isDarkTheme.value = event.matches;
});
document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');

// ========== Handle articles ==========
const articles = ref([]);

const fetchFeed = async (lastId = null) => {
  try {
    const response = await axios.get(apiOrigin + "api/v1/feed/", {params: {language: lang.value, cursor: lastId}});
    const responseData = response.data[0]; // Directly access the first element of the array
    // append all the dictionaries to the articles array
    articles.value.push(...responseData);
    console.log("Parsed data:", responseData);

  } catch (error) {
    console.error("Error fetching language config:", error);
  }
}


// ========== On mounted ==========
onMounted(() => {
  themeChange(true);
  fetchFeed();
});


</script>