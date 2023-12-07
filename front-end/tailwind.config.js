/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./index.html",
        "./src/**/*.{vue,js,ts,jsx,tsx}",
    ],
    theme: {
        fontFamily: {
            'sans': ['Inter', 'sans-serif'],
        },
        extend: {},
    },
    plugins: [
        require("@tailwindcss/typography"),
        require("daisyui")],
    daisyui: {
        darkTheme: "dark", // name of one of the included themes for dark mode
        base: true, // applies background color and foreground color for root element by default
        styled: true, // include daisyUI colors and design decisions for all components
        utils: true, // adds responsive and modifier utility classes
        prefix: "", // prefix for daisyUI classnames (components, modifiers and responsive class names. Not colors)
        logs: true, // Shows info about daisyUI version and used config in the console when building your CSS
        themeRoot: ":root", // The element that receives theme color CSS variables
        themes: [
            {
                theRealmOfTwilightSerenity: {
                    "primary": "#FBDE82",
                    "primary-content": "#F1F3F9",
                    "secondary": "#747CD1",
                    "accent": "#F38D45",
                    "neutral": "#10121A",
                    "base-100": "#040A0F",
                    "base-200": "#071119",
                    "base-300": "#0A1925",
                    "base-content": "#F5F1EF",
                    "info": "#10121A",
                },
            },
            {
                theLandofMorningCalm: {
                    "primary": "#FBD373",
                    "secondary": "#2C3E68",
                    "accent": "#EB8A4E",
                    "neutral": "#10121A",
                    "base-100": "#FAF8F4",
                    "base-200": "#F2F0EC",
                    "base-300": "#ECEAE6",
                    "base-content": "#020614",
                    "info": "#01090F",
                    "info-content": "#F5ECD5",
                },
            }
        ],
    }
}