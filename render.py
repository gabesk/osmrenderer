import xml.etree.ElementTree as etree
import xml.parsers.expat
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

nodes = {}
ways = {}

class Map(object):
    '''Parses a file containing OSM XML data
    (http://wiki.openstreetmap.org/wiki/OSM_XML) into nodes and ways dicts keyed
    by node and way id attribute. Use expat parser instead of a DOM-based one
    to allow parsing larger maps without running out of memory.'''
    def __init__(self, map_filename):
        self.nodes = {}
        self.ways = {}
        self._nds = []
        self._way = None
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = None, None, None, None

        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = lambda name, attrs: Map.start_element(self, name, attrs)
        p.EndElementHandler = lambda name: Map.end_element(self, name)
        p.CharacterDataHandler = lambda data: Map.char_data(self, data)

        print 'Opening ' + map_filename
        map_filehandle = open(map_filename, 'rb')
        print 'done'

        print 'Parsing'
        p.ParseFile(map_filehandle)
        print 'done'

    def start_element(self, name, attrs):
        if name == 'node':
            if u'id' in attrs:
                self.nodes[attrs[u'id']] = (attrs[u'uid'], float(attrs[u'lat']), float(attrs[u'lon']))
        elif name == 'way':
            self._nds = []
            self._way = {}
            self._way[u'id'] = attrs[u'id']
            self._way[u'uid'] = attrs[u'uid']

        if self._way:
            if name == 'nd':
                self._nds.append(attrs[u'ref'])
            elif name == 'tag':
                self._way[attrs[u'k']] = attrs[u'v']

    def end_element(self, name):
        if name == 'way':
            self._way[u'nds'] = self._nds
            self.ways[self._way[u'id']] = self._way
            self._way = None

    def char_data(self, data):
        pass

    def bounds(self):
        # Use cached results if already available
        if self._lon_min:
            return self._lon_min, self._lon_max, self._lat_min, self._lat_max

        print 'Finding bounding box'
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = 180.0, -180.0, 180.0, -180.0
        for id, node in self.nodes.iteritems():
            uid, lat, lon = node
            if lon < self._lon_min:
                self._lon_min = lon
            elif lon > self._lon_max:
                self._lon_max = lon

            if lat < self._lat_min:
                self._lat_min = lat
            elif lat > self._lat_max:
                self._lat_max = lat

        print self._lon_min, self._lon_max, self._lon_max - self._lon_min
        print self._lat_min, self._lat_max, self._lat_max - self._lat_min
        print 'done'
        return self._lon_min, self._lon_max, self._lat_min, self._lat_max

class Renderer(object):
    def __init__(self, map, size):
        self.nodes = map.nodes
        self.ways = map.ways
        self._lon_min, self._lon_max, self._lat_min, self._lat_max = map.bounds()
        self.ratio = (self._lat_max - self._lat_min) / (self._lon_max - self._lon_min)
        self.width = size
        self.height = int(self.width * self.ratio)

    def _highway_width(self, highway):
        '''The following types of highways exist in OSM:
            highway=motorway fast, restricted access road
            highway=trunk most important in standard road network
            highway=primary down to
            highway=secondary
            highway=tertiary
            highway=unclassified least important in standard road network
            highway=residential smaller road for access mostly to residential properties
            highway=service smaller road for access, often but not exclusively to non-residential properties'''
        if highway == u'motorway':
            width = 20
        elif highway == u'trunk':
            width = 18
        elif highway == u'primary':
            width = 16
        elif highway == u'secondary':
            width = 14
        elif highway == u'tertiary':
            width = 12
        elif highway == u'unclassified':
            width = 8
        elif highway == u'residential':
            width = 6
        elif highway == u'service':
            width = 4
        else:
            width = 2
        return width

    def _transform_to_screen_px(self, lon, lat):
        lon_norm = (lon - self._lon_min) / (self._lon_max - self._lon_min)
        lat_norm = (lat - self._lat_min) / (self._lat_max - self._lat_min)
        lon_px = lon_norm * (self.width-1)
        lat_px = lat_norm * (self.height-1)
        return int(lon_px), (self.height-int(lat_px)-1)

    def create_png(self, filename):
        im = Image.new("RGB", (self.width, self.height), "white")
        print 'Printing lines'
        draw = ImageDraw.Draw(im)
        for id, way in self.ways.iteritems():
            last_x, last_y = None, None
            for nd in way[u'nds']:
                node = self.nodes[nd]
                uid, lat, lon = node
                x, y = self._transform_to_screen_px(lon, lat)
                if last_x:
                    if u'highway' in way:
                        #print way[u'highway']
                        width = self._highway_width(way[u'highway'])
                    else:
                        width = 1
                    draw.line(((last_x, last_y), (x, y)), fill=(0x33, 0x99, 0xFF), width=width)
                last_x, last_y = x, y
        print 'done'
        print 'Printing dots'
        for id, node in self.nodes.iteritems():
            uid, lat, lon = node
            x, y = self._transform_to_screen_px(lon, lat)
            im.putpixel((x,y), 0x0000FF) # red color
        print 'done'
        # For now the label algorithm is simple to the point of almost being useless; place the text at the midpoint of the way
        print 'Printing labels'
        for id, way in self.ways.iteritems():
            if u'name' in way:
                midpoint_nd = way[u'nds'][len(way[u'nds'])/2]
                midpoint_node = self.nodes[midpoint_nd]
                uid, lat, lon = midpoint_node
                x, y = self._transform_to_screen_px(lon, lat)
                tx, ty = draw.textsize(way[u'name'])
                draw.text((x - tx / 2,y), way[u'name'], fill=0)
        print 'done'
        im.save(filename)

map_obj = Map('map.osm')
rend_obj = Renderer(map_obj, 2000)
rend_obj.create_png('test.png')