<template>
  <div :class="`font-${lang}`">
    <div class="navbar bg-base-100 top-0 bg-opacity-80 backdrop-blur fixed z-10 sm:px-4 shadow-sm">
      <!-- Left Side -->
      <div class="navbar-start space-x-2" >
        <div class="btn btn-ghost" @click="scrollToTop">
          <img src="/src/assets/logo.png" alt="Joseon Space Logo" class="h-6 w-auto">
          <p class="text-md font-bold">{{ langData.title }}</p>
        </div>
      </div>

      <!-- Right Side -->
      <div class="navbar-end px-0">
        <!-- Theme Controller -->
        <div class="tooltip tooltip-bottom" v-bind:data-tip="langData.themeTooltip">
          <div class="btn btn-ghost" @click="isDarkTheme = !isDarkTheme">
            <label class="swap swap-rotate">
              <!-- change checkbox value to isDarkTheme while preventing the checkbox from being clicked by user -->
              <input type="checkbox" :checked="isDarkTheme" disabled/>
              <sun-icon class="swap-on fill-current h-5 w-auto"/>
              <moon-icon class="swap-off fill-current h-5 w-auto"/>
            </label>
          </div>
        </div>
        <!-- Language Controller -->
        <div class="flex items-stretch">
          <div class="dropdown dropdown-end">
            <div class="btn btn-ghost" tabindex="0">
              <LanguageIcon class="h-5 w-auto"/>
              <img class="h-4 w-auto hidden sm:block" alt="Flag" :src="`/src/assets/lang-icon/${lang}.svg`">
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

    <!--  Main Content  -->
    <div class="flex justify-center items-center w-full h-screen bg-cover bg-center bg-no-repeat"
         :style="`background-image: url('/src/assets/hero-${isDarkTheme ? 'dark' : 'light'}.jpg')`">
      <div class="absolute bottom-1/2 max-w-xl w-full px-4">
        <div class="flex justify-center items-center p-4 space-x-4">
          <img src="/src/assets/logo.png" alt="Joseon Space Logo" class="sm:w-14 w-12">
          <p class="text-2xl sm:text-3xl font-bold">
            <span class="text-transparent bg-clip-text bg-gradient-to-br from-primary to-accent"> {{
                langData.joseonSpace
              }}</span> <span class="text-secondary"> {{ langData.title }} </span>
          </p>
        </div>

        <div class="join w-full">
          <input type="text" :placeholder="langData.searchPlaceholder"
                 class="input bg-none input-bordered input-primary w-full join-item"/>
          <button class="btn btn-primary join-item">
            <MagnifyingGlassIcon class="h-4 w-auto"></MagnifyingGlassIcon>
          </button>
        </div>

        <p class="p-2 text-sm font-light">
          <span class="font-semibold text-primary">{{ indexedCount }}</span> {{ langData.indexCount }}
        </p>
      </div>
    </div>

    <!--  Back to top button, shown afetr scrolling past the main content  -->
    <div class="fixed bottom-4 right-4">
      <button class="btn btn-accent btn-circle btn-outline" @click="scrollToTop">
        <ArrowUpIcon class="h-6 w-6"></ArrowUpIcon>
      </button>
    </div>

    <!--  Preview Prompt  -->
    <div class="absolute w-full bottom-1 sm:pb-10 pb-6">
      <div class="flex justify-center items-center p-2">
        <p class="font-bold text-lg">{{ langData.scrollForRecent }}</p>
      </div>
      <div class="flex justify-center items-center">
        <ArrowDownCircleIcon class="h-6 w-auto"></ArrowDownCircleIcon>
      </div>
    </div>

    <!--  Recent Contents  -->
    <div class="flex justify-center items-center sm:px-8 px-2 py-6">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-screen-lg">
        <div class="card bg-base-200 shadow-2xl h-96 overflow-clip" v-for="article in articles">
          <div class="card-body">
            <h2 class="card-title">
              {{ article.title }}
            </h2>
            <article class="prose prose-sm leading-tight" v-html="markdown.render(article.content)"/>
          </div>
          <div class="absolute bottom-1 w-full h-1/4 translate-y-1 bg-gradient-to-t from-base-200 from-30%"/>
          <div class="card absolute w-full h-full outline outline-primary -outline-offset-8"/>
        </div>
      </div>
    </div>
  </div>
</template>


<script setup>
import {
  LanguageIcon,
  ChevronDownIcon,
  SunIcon,
  MoonIcon,
  MagnifyingGlassIcon,
  ArrowDownCircleIcon,
  ArrowUpIcon
} from '@heroicons/vue/24/solid'
import {onMounted, reactive, ref, watch} from 'vue'
import {themeChange} from 'theme-change'
import axios from 'axios'
import MarkdownIt from "markdown-it";

const markdown = new MarkdownIt().disable(['image', 'heading', 'code', 'table']);
const apiOrigin = "http://127.0.0.1:8000/"

// ========== Language Management ==========
// Ref to store the current language
const lang = ref('en');
// Set index count
let indexedCount = ref(0);
// Reactive dictionary for language data
const langData = reactive({
  title: "Luma",
  joseonSpace: "Joseon Space Luma",
  themeTooltip: "Toggle light/dark theme",
  searchPlaceholder: "Search all notices",
  scrollForRecent: "Scroll down browse recent news",
  indexCount: "article indexed & translated"
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

const infiniteScroll = () => {
  const scrollHeight = document.documentElement.scrollHeight;
  const scrollTop = document.documentElement.scrollTop;
  const clientHeight = document.documentElement.clientHeight;
  if (scrollTop + clientHeight >= scrollHeight) {
    console.log("Reached bottom of page");
    fetchFeed(articles.value[articles.value.length - 1].id);
  }
}

window.addEventListener('scroll', infiniteScroll);

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

const scrollToTop = () => {
  console.log("Scroll to top triggered");
  window.scrollTo({top: 0, behavior: 'smooth'});
}

// ========== Theme Management ==========
const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
const isDarkTheme = ref(prefersDark);
watch(isDarkTheme, (newValue) => {
  console.log("Theme changed:", newValue);
  document.documentElement.setAttribute('data-theme', newValue ? 'theRealmOfTwilightSerenity' : 'theLandofMorningCalm');
});
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
  isDarkTheme.value = event.matches;
});
document.documentElement.setAttribute('data-theme', prefersDark ? 'theRealmOfTwilightSerenity' : 'theLandofMorningCalm');

// ========== Handle articles ==========
let articles = ref([]);

const fetchFeed = async (lastId = null) => {
  console.log("Fetching feed with last id:", lastId);
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

const getIndexCount = async () => {
  try {
    const response = await axios.get(apiOrigin + "api/v1/articles/count/");
    console.log("Index count:", response.data[0]);
    indexedCount.value = response.data[0];
  } catch (error) {
    console.error("Error fetching index count:", error);
  }
}


// ========== On mounted ==========
onMounted(() => {
  getIndexCount();
  themeChange(true);
  fetchFeed();
});


</script>