"""
LARA RODRIGUEZ CUENCA (1667906)
SARA MARTIN NÚÑEZ (1669812)
AINA NAVARRO RAFOLS (16770797)
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy
import re
from scipy.spatial import Voronoi, voronoi_plot_2d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, FOAF, DC
from owlready2 import get_ontology, Thing, ObjectProperty, DataProperty


# ---------------------------------------------------------------#
# ---------------Functions for color analysis--------------------#
# ---------------------------------------------------------------#

HUE = {"red": ["Y50R","Y60R","Y70R","Y80R","Y90R","R","R10B","R20B","R30B","R40B"],
       "blue": ["R50B","R60B","R70B","R80B","R90B","B","B10G","B20G","B30G","B40G"],
       "green": ["B50G","B60G","B70G","B80G","B90G","G","G10Y","G20Y","G30Y","G40Y"],
       "yellow": ["G50Y","G60Y","G70Y","G80Y","G90Y","Y","Y10R","Y20R","Y30R","Y40R"]}

# Define Voronoi Teselation
COLOR_SPACE = {'RED': (255, 0, 0),
               'BLUE': (0, 0, 255),
               'GREEN': (0, 255, 0),
               'YELLOW': (255, 255, 0),
               'BLACK': (0, 0, 0),
               'WHITE': (255, 255, 255)}

POINTS = np.array([value for value in COLOR_SPACE.values()])
VOR = Voronoi(POINTS)

# First approach
def ncs_1(color: str) -> str:
    """
    Get the primary color name from Natural Color System format.

    :param: color: string of color in NCS format
    :param: hue: dictionary with primary colors associated to NCS
    :returns: primary color name string
    """
    if len(color.split(' ')) == 1:
        return color

    # Get parts of NSC
    splitted = re.split(r'[ -]+', color)

    s = int(splitted[2][0:2])
    c = int(splitted[2][2:4])
    hue_value = splitted[3]

    # Get primary color
    # If the chromaticness is lower than 10, we associate to black or white.
    if (c < 10) and (s >= 40):
        # If the blackness is equal or higher than 40%, it is black.
        return "black"
    elif (c < 10) and (s < 40):
        # If the blackness is lower than 40%, it is white.
        return "white"
    else: # If the chromaticness is equal or higher than 10, we associate to a primary color.
        for key,values in HUE.items():
            if hue_value in values:
                return key


def read_ncs_rgb_file(file_path) -> dict:
    """
    Reads the txt file with NCS to RGB conversions and stores
    values in a dictionary where key = NCS and value = (r,g,b).
    :param: file_path: string with the file_path of the txt file.
    :returns: dictionary with conversions.
    """
    ncs_rgb_dict = {}

    with open(file_path, 'r') as file:
        for line in file:  
            parts = line.split()
            ncs_name = str(parts[0]) + " " + str(parts[1])
            r, g, b = int(parts[-3]), int(parts[-2]), int(parts[-1])
            ncs_rgb_dict[ncs_name] = r, g, b

    return ncs_rgb_dict


# Second approach
def ncs(color:str) ->str:
    """
    Gives the primary color of a NCS color using Voronoi Teselation.
    :param: color: string with the color in NCS format.
    :returns: result: string with the primary color.
    """
    if len(color.split(' ')) == 1:
        return color
    
    # Get RGB value of the color
    value = ncs_rgb_dict[color[4:]]

    # Find closest area in the color space
    # Compute the distances between the input color and the prototype colors
    distances = [(i, np.linalg.norm(np.array(value) - np.array(p))) for i, p in enumerate(POINTS)]
    # Sort the distances by distance value
    distances.sort(key=lambda x: x[1])
    # The closest prototype color is the one with the smallest distance
    result = list(COLOR_SPACE.keys())[distances[0][0]]
    
    return result


# Get NCS to RGB conversions
file_path = 'ncs_rgb.txt'
ncs_rgb_dict = read_ncs_rgb_file(file_path)


# ---------------------------------------------------------------#
# ---------------------------------------------------------------#


# Load your ontology
onto = get_ontology("ontology_unpopulated.owl").load()

# Load your data
g = Graph()
g.parse("roadsign-data_modified.ttl", format="turtle")


# Define your namespaces
RSS = Namespace("http://www.iiia.csic.es/~marco/kr/roadsign-schema#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DC = Namespace("http://purl.org/dc/elements/1.1/")

instances = {}
# Get all instances
for s, p, o in g:
    
    #If object is of class road_sign we create instance
    if p == RDF.type and o == RSS.road_sign: 
        instances[s] = onto.RoadSign()
        
        list_properties = []
        # Iterate over properties of our current roadsign
        for prop, value in g.predicate_objects(s):
            property_name = prop.split("#")[-1]
            list_properties.append(property_name)
            value = str(value)
            if property_name == "shape":
                instances[s].shape = [onto.Shape(value.replace(" ","_").upper())]
            elif property_name == "border_colour":
                instances[s].borderColor = [onto.Color(ncs(value).replace(" ","_").upper())]
            elif property_name == "ground_colour":
                instances[s].groundColor = [onto.Color(ncs(value).replace(" ","_").upper())]
            elif property_name == "symbol":
                instances[s].symbol = [onto.Symbol(value.replace(" ","_").upper())]
            elif property_name == "symbol_colour":
                instances[s].symbolColor = [onto.Color(ncs(value).replace(" ","_").upper())]
            elif property_name == "symbol_value":
                value = value.replace(" ","_").replace(',', '.').replace("%","PERCENT").upper()
                instances[s].symbolValue = [value]

        if "symbol" not in list_properties:
            instances[s].symbol = [onto.Symbol("NO_SYMBOL")]
        
        # Linking the image to the road sign depicted
        for subj, pred, obj in g:
            if pred == FOAF.depicts and obj == s:
                instances[s].image = [str(subj)]
                image_uri = subj
                break
        
        # Add date and creator properties to image
        for subj, pred, obj in g:
            if subj == image_uri and pred == DC.creator:
                instances[s].imageCreator = [str(obj)]
            if subj == image_uri and pred == DC.date:
                instances[s].imageDate = [str(obj)] 
        

# Save ontology
onto.save(file="ontology_populated_nsc.owl")





