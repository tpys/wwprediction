from matplotlib.colors import ListedColormap



## COLOR MAPS
# define color maps for when the matplotlib ones arent very good
# color maps created with this amazing online hex gradient color generator
# http://www.strangeplanet.fr/work/gradient-generator/index.php

precip_colors = [
    "#04e9e7",  # 0.01 - 0.10 inches
    "#019ff4",  # 0.10 - 0.25 inches
    "#0300f4",  # 0.25 - 0.50 inches
    "#02fd02",  # 0.50 - 0.75 inches
    "#01c501",  # 0.75 - 1.00 inches
    "#008e00",  # 1.00 - 1.50 inches
    "#fdf802",  # 1.50 - 2.00 inches
    "#e5bc00",  # 2.00 - 2.50 inches
    "#fd9500",  # 2.50 - 3.00 inches
    "#fd0000",  # 3.00 - 4.00 inches
    "#d40000",  # 4.00 - 5.00 inches
    "#bc0000",  # 5.00 - 6.00 inches
    "#f800fd",  # 6.00 - 8.00 inches
    "#9854c6",  # 8.00 - 10.00 inches
    "#fdfdfd"]   # 10.00+

dbz_colors = [
    "#FFFFFF", # 0
    "#808080", # 5
    "#00FFFF", # 5-10
    "#00BFFF", # 10-15
    "#0000FF", # 15-20
    "#00FF00", # 20-25
    "#32CD32", # 25-30
    "#008000", # 30-35
    "#FFFF00", # 35-40
    "#DAA520", # 40-45
    "#FFA500", # 45-50
    "#FF0000", # 50-55
    "#8B0000", # 55-60
    "#800000", # 60-65
    "#FF00FF", # 65-70
    "#8A2BE2", # 70-75
    "#FFFFFF"] # 75+

lcl_colors = ["#FFFFFF", #0 m
              "#867FFF", #500
              "#0D00FF", #1000
              "#0B7F7F", #1500
              "#09FF00", #2000
              "#84D200", #2500
              "#FFA600", #3000
              "#FF5300", #3500
              "#FF0000", #4000
              "#FF0075", #4500
              "#FF00EA"] #5000


snow_colors = ["#FFFFFF", "#C2BFFF", "#867FFF", "#493FFF", "#0D00FF", "#0C3FBF", "#0B7F7F", "#0ABF3F", "#09FF00", "#46E800", "#84D200", "#C1BC00", "#FFA600", "#FF7C00", "#FF5300", "#FF2900", "#FF0000", "#FF004E", "#FF009C", "#FF00EA"]

hail_colors = ["#FFFFFF", "#AEAAFF", "#5D55FF", "#0D00FF", "#0B55AA", "#0AAA55", "#09FF00", "#5BE100", "#ADC300", "#FFA600", "#FF6E00", "#FF3700", "#FF0000", "#FF0075", "#FF00EA"]

irsat_colors = ["#D2D2D2", "#DD9D9D", "#E86969", "#F33434", "#FF0000", "#FF3E00", "#FF7D00", "#FFBC00", "#FFFB00", "#AAFC00", "#55FD00", "#00FF00", "#00AA55", "#0055AA", "#0000FF", "#D2D2D2", "#C3C3C3", "#B4B4B4", "#A5A5A5", "#969696", "#878787", "#787878", "#696969", "#5A5A5A", "#4A4A4A", "#3C3C3C", "#2D2D2D", "#1E1E1E", "#0E0E0E", "#000000"]


precip = ListedColormap(precip_colors)
dbz = ListedColormap(dbz_colors)              
lcl = ListedColormap(lcl_colors)
snow = ListedColormap(snow_colors)
hail = ListedColormap(hail_colors)
irsat = ListedColormap(irsat_colors)